/*
 * xttap.c
 *
 * Prototype Xt/Motif widget introspection hook.
 *
 * Purpose
 * -------
 * This library is intended to be preloaded into a dynamically linked Xt/Motif
 * application. It observes widget lifecycle/configuration events and writes two
 * files:
 *
 *   MOTIF_TAP_STATE : current widget tree as JSON
 *   MOTIF_TAP_LOG   : timestamped JSON Lines snapshots
 *
 * The Python test harness reads MOTIF_TAP_STATE while replaying tests. The
 * translator reads MOTIF_TAP_LOG to map recorded Xnee coordinates to Xt widget
 * paths.
 *
 * Build
 * -----
 *   make -C c
 *
 * Use
 * ---
 *   MOTIF_TAP_STATE=/tmp/motif/latest-state.json \
 *   MOTIF_TAP_LOG=/tmp/motif/widgets.jsonl \
 *   LD_PRELOAD=$PWD/c/libxttap.so \
 *   ./my_motif_app
 *
 * Notes
 * -----
 * This is a starter implementation. It intentionally favors clarity over
 * maximum portability. It uses Xt private headers to traverse widget children.
 * Most Xt/Motif development installations provide these headers, but package
 * names vary by platform.
 */

#define _GNU_SOURCE

#include <X11/Intrinsic.h>
#include <X11/IntrinsicP.h>
#include <X11/CoreP.h>
#include <X11/CompositeP.h>
#include <X11/Shell.h>
#include <X11/StringDefs.h>

#include <dlfcn.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

#define TAP_MAX_ROOTS 256
#define TAP_PATH_MAX 4096
static Widget tap_roots[TAP_MAX_ROOTS];
static int tap_root_count = 0;
static int tap_dumping = 0;
static int tap_hooks_installed = 0;
static char *tap_last_log_snapshot = NULL;

static const char *tap_state_path(void) {
    const char *p = getenv("MOTIF_TAP_STATE");
    return p && *p ? p : "/tmp/motif-tap-latest-state.json";
}

static const char *tap_log_path(void) {
    const char *p = getenv("MOTIF_TAP_LOG");
    return p && *p ? p : "/tmp/motif-tap-widgets.jsonl";
}

static int tap_debug_enabled(void) {
    const char *p = getenv("MOTIF_TAP_DEBUG");
    return p && *p && strcmp(p, "0") != 0;
}

static void tap_debug(const char *fmt, ...) {
    if (!tap_debug_enabled()) return;

    va_list ap;
    va_start(ap, fmt);
    fputs("motif-tap: ", stderr);
    vfprintf(stderr, fmt, ap);
    fputc('\n', stderr);
    va_end(ap);
}

static double tap_now_seconds(void) {
    struct timespec ts;
#if defined(CLOCK_MONOTONIC)
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + ((double)ts.tv_nsec / 1000000000.0);
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (double)tv.tv_sec + ((double)tv.tv_usec / 1000000.0);
#endif
}

static void tap_json_string(FILE *f, const char *s) {
    fputc('"', f);
    if (s) {
        for (const unsigned char *p = (const unsigned char *)s; *p; ++p) {
            switch (*p) {
                case '"': fputs("\\\"", f); break;
                case '\\': fputs("\\\\", f); break;
                case '\b': fputs("\\b", f); break;
                case '\f': fputs("\\f", f); break;
                case '\n': fputs("\\n", f); break;
                case '\r': fputs("\\r", f); break;
                case '\t': fputs("\\t", f); break;
                default:
                    if (*p < 0x20) {
                        fprintf(f, "\\u%04x", *p);
                    } else {
                        fputc(*p, f);
                    }
            }
        }
    }
    fputc('"', f);
}

static const char *tap_widget_name(Widget w) {
    if (!w) return "";
    const char *name = XtName(w);
    return name ? name : "";
}

static const char *tap_widget_class_name(Widget w) {
    if (!w || !w->core.widget_class) return "";
    const char *name = w->core.widget_class->core_class.class_name;
    return name ? name : "";
}

static const char *tap_path_segment_name(Widget w) {
    const char *name = tap_widget_name(w);
    if (!name || !*name) name = tap_widget_class_name(w);
    if (!name || !*name) name = "widget";
    return name;
}

static int tap_sibling_duplicate_count(Widget w, const char *name) {
    Widget parent = XtParent(w);
    if (!parent || !XtIsComposite(parent)) return 1;

    int count = 0;
    CompositeWidget cw = (CompositeWidget)parent;
    for (Cardinal i = 0; i < cw->composite.num_children; ++i) {
        if (strcmp(tap_path_segment_name(cw->composite.children[i]), name) == 0) {
            count++;
        }
    }
    return count;
}

static int tap_sibling_index(Widget w, const char *name) {
    Widget parent = XtParent(w);
    if (!parent || !XtIsComposite(parent)) return 0;

    int index = 0;
    CompositeWidget cw = (CompositeWidget)parent;
    for (Cardinal i = 0; i < cw->composite.num_children; ++i) {
        Widget child = cw->composite.children[i];
        if (strcmp(tap_path_segment_name(child), name) == 0) {
            if (child == w) return index;
            index++;
        }
    }
    return 0;
}

static Widget tap_root_of(Widget w) {
    if (!w) return NULL;
    while (XtParent(w)) {
        w = XtParent(w);
    }
    return w;
}

static void tap_remember_root(Widget w) {
    Widget root = tap_root_of(w);
    if (!root) return;

    for (int i = 0; i < tap_root_count; ++i) {
        if (tap_roots[i] == root) return;
    }

    if (tap_root_count < TAP_MAX_ROOTS) {
        tap_roots[tap_root_count++] = root;
    }
}

static void tap_build_path(Widget w, char *buf, size_t n) {
    Widget stack[512];
    int count = 0;

    for (Widget cur = w; cur && count < 512; cur = XtParent(cur)) {
        stack[count++] = cur;
    }

    buf[0] = '\0';
    for (int i = count - 1; i >= 0; --i) {
        const char *name = tap_path_segment_name(stack[i]);

        if (buf[0] != '\0') {
            strncat(buf, ".", n - strlen(buf) - 1);
        }
        strncat(buf, name, n - strlen(buf) - 1);
        if (tap_sibling_duplicate_count(stack[i], name) > 1) {
            char suffix[32];
            snprintf(suffix, sizeof(suffix), "[%d]", tap_sibling_index(stack[i], name));
            strncat(buf, suffix, n - strlen(buf) - 1);
        }
    }
}

static int tap_widget_depth(Widget w) {
    int depth = 0;
    for (Widget cur = w; cur && XtParent(cur); cur = XtParent(cur)) {
        depth++;
    }
    return depth;
}

static int tap_is_managed(Widget w) {
    if (!w) return 0;
    return w->core.managed ? 1 : 0;
}

static int tap_is_sensitive(Widget w) {
    if (!w) return 0;
    return XtIsSensitive(w) ? 1 : 0;
}

static int tap_widget_root_xy(Widget w, int *rx, int *ry) {
    *rx = 0;
    *ry = 0;

    if (!w) return 0;

    Position offset_x = 0;
    Position offset_y = 0;
    Widget anchor = w;
    while (anchor && !XtIsRealized(anchor)) {
        offset_x += anchor->core.x;
        offset_y += anchor->core.y;
        anchor = XtParent(anchor);
    }

    if (!anchor) {
        for (int i = 0; i < tap_root_count; ++i) {
            if (tap_roots[i] && XtIsRealized(tap_roots[i])) {
                anchor = tap_roots[i];
                break;
            }
        }
    }

    if (!anchor) return 0;

    Position x = 0;
    Position y = 0;
    XtTranslateCoords(anchor, offset_x, offset_y, &x, &y);
    *rx = (int)x;
    *ry = (int)y;
    return 1;
}

static void tap_write_widget(FILE *f, Widget w, int *first) {
    if (!w) return;

    char path[TAP_PATH_MAX];
    tap_build_path(w, path, sizeof(path));

    int root_x = 0;
    int root_y = 0;
    int has_root_xy = tap_widget_root_xy(w, &root_x, &root_y);

    if (!*first) {
        fputc(',', f);
    }
    *first = 0;

    fprintf(f, "{");
    fputs("\"path\":", f); tap_json_string(f, path); fputc(',', f);
    fputs("\"name\":", f); tap_json_string(f, tap_widget_name(w)); fputc(',', f);
    fputs("\"class\":", f); tap_json_string(f, tap_widget_class_name(w)); fputc(',', f);

    if (XtIsRealized(w)) {
        fprintf(f, "\"window\":\"0x%lx\",", (unsigned long)XtWindow(w));
    } else {
        fputs("\"window\":null,", f);
    }

    fprintf(
        f,
        "\"root_x\":%d,\"root_y\":%d,\"x\":%d,\"y\":%d,"
        "\"width\":%u,\"height\":%u,\"border_width\":%u,"
        "\"depth\":%d,\"managed\":%s,\"sensitive\":%s,\"realized\":%s",
        root_x,
        root_y,
        (int)w->core.x,
        (int)w->core.y,
        (unsigned int)w->core.width,
        (unsigned int)w->core.height,
        (unsigned int)w->core.border_width,
        tap_widget_depth(w),
        tap_is_managed(w) ? "true" : "false",
        tap_is_sensitive(w) ? "true" : "false",
        has_root_xy ? "true" : "false"
    );

    fprintf(f, "}");
}

static void tap_walk(FILE *f, Widget w, int *first) {
    if (!w) return;

    tap_write_widget(f, w, first);

    if (XtIsComposite(w)) {
        CompositeWidget cw = (CompositeWidget)w;
        for (Cardinal i = 0; i < cw->composite.num_children; ++i) {
            tap_walk(f, cw->composite.children[i], first);
        }
    }
}

static void tap_write_snapshot(FILE *f, double t) {
    fprintf(f, "{\"type\":\"snapshot\",\"t\":%.9f,\"widgets\":[", t);
    int first = 1;

    for (int i = 0; i < tap_root_count; ++i) {
        Widget root = tap_roots[i];
        if (root) {
            tap_walk(f, root, &first);
        }
    }

    fputs("]}", f);
}

static void tap_write_widgets(FILE *f) {
    int first = 1;

    for (int i = 0; i < tap_root_count; ++i) {
        Widget root = tap_roots[i];
        if (root) {
            tap_walk(f, root, &first);
        }
    }
}

static void tap_dump_state(void) {
    if (tap_dumping) return;
    tap_dumping = 1;

    const char *state_path = tap_state_path();
    const char *log_path = tap_log_path();
    double t = tap_now_seconds();

    char tmp_path[PATH_MAX];
    snprintf(tmp_path, sizeof(tmp_path), "%s.tmp.%ld", state_path, (long)getpid());

    FILE *state = fopen(tmp_path, "w");
    if (state) {
        tap_write_snapshot(state, t);
        fputc('\n', state);
        fflush(state);
        fsync(fileno(state));
        fclose(state);
        if (rename(tmp_path, state_path) != 0) {
            tap_debug(
                "failed to rename state file %s to %s: %s",
                tmp_path,
                state_path,
                strerror(errno)
            );
        }
    } else {
        tap_debug("failed to open state file %s: %s", tmp_path, strerror(errno));
    }

    char *snapshot = NULL;
    size_t snapshot_size = 0;
    FILE *widgets_stream = open_memstream(&snapshot, &snapshot_size);
    if (widgets_stream) {
        tap_write_widgets(widgets_stream);
        fclose(widgets_stream);

        if (!tap_last_log_snapshot || strcmp(tap_last_log_snapshot, snapshot) != 0) {
            FILE *log = fopen(log_path, "a");
            if (log) {
                fprintf(log, "{\"type\":\"snapshot\",\"t\":%.9f,\"widgets\":[", t);
                fputs(snapshot, log);
                fputs("]}", log);
                fputc('\n', log);
                fclose(log);
                free(tap_last_log_snapshot);
                tap_last_log_snapshot = snapshot;
                snapshot = NULL;
            } else {
                tap_debug("failed to open widget log %s: %s", log_path, strerror(errno));
            }
        }
        free(snapshot);
    } else {
        tap_debug("failed to allocate widget snapshot stream");
    }

    tap_dumping = 0;
}

static void tap_note_widget(Widget w) {
    if (!w) return;
    Widget root = tap_root_of(w);
    tap_remember_root(w);
    if (!root || !XtIsRealized(root)) return;
    tap_dump_state();
}

static void tap_create_cb(Widget hook, XtPointer client_data, XtPointer call_data) {
    (void)hook;
    (void)client_data;
    XtCreateHookData data = (XtCreateHookData)call_data;
    if (data && data->widget) tap_note_widget(data->widget);
}

static void tap_change_cb(Widget hook, XtPointer client_data, XtPointer call_data) {
    (void)hook;
    (void)client_data;
    XtChangeHookData data = (XtChangeHookData)call_data;
    if (data && data->widget) tap_note_widget(data->widget);
}

static void tap_configure_cb(Widget hook, XtPointer client_data, XtPointer call_data) {
    (void)hook;
    (void)client_data;
    XtConfigureHookData data = (XtConfigureHookData)call_data;
    if (data && data->widget) tap_note_widget(data->widget);
}

static void tap_geometry_cb(Widget hook, XtPointer client_data, XtPointer call_data) {
    (void)hook;
    (void)client_data;
    XtGeometryHookData data = (XtGeometryHookData)call_data;
    if (data && data->widget) tap_note_widget(data->widget);
}

static void tap_destroy_cb(Widget hook, XtPointer client_data, XtPointer call_data) {
    (void)hook;
    (void)client_data;
    XtDestroyHookData data = (XtDestroyHookData)call_data;
    if (data && data->widget) tap_note_widget(data->widget);
}

static void tap_install_hooks_for_display(Display *dpy) {
    if (!dpy || tap_hooks_installed) return;

    Widget hooks = XtHooksOfDisplay(dpy);
    if (!hooks) {
        tap_debug("XtHooksOfDisplay returned no hooks");
        return;
    }

    XtAddCallback(hooks, XtNcreateHook, tap_create_cb, NULL);
    XtAddCallback(hooks, XtNchangeHook, tap_change_cb, NULL);
    XtAddCallback(hooks, XtNconfigureHook, tap_configure_cb, NULL);
    XtAddCallback(hooks, XtNgeometryHook, tap_geometry_cb, NULL);
    XtAddCallback(hooks, XtNdestroyHook, tap_destroy_cb, NULL);

    tap_hooks_installed = 1;
}

/*
 * Wrappers below are intentionally small. They help install hooks even if the
 * application does not call an Xt initialization symbol we can easily intercept.
 */

typedef Display *(*real_XtOpenDisplay_fn)(XtAppContext, _Xconst _XtString, _Xconst _XtString, _Xconst _XtString, XrmOptionDescRec *, Cardinal, int *, _XtString *);
Display *XtOpenDisplay(XtAppContext app_context, _Xconst _XtString display_string, _Xconst _XtString application_name,
                       _Xconst _XtString application_class, XrmOptionDescRec *options, Cardinal num_options,
                       int *argc, _XtString *argv) {
    real_XtOpenDisplay_fn real_fn = (real_XtOpenDisplay_fn)dlsym(RTLD_NEXT, "XtOpenDisplay");
    if (!real_fn) {
        tap_debug("could not resolve XtOpenDisplay: %s", dlerror());
        return NULL;
    }
    Display *dpy = real_fn(app_context, display_string, application_name, application_class,
                           options, num_options, argc, argv);
    tap_install_hooks_for_display(dpy);
    return dpy;
}

typedef void (*real_XtDisplayInitialize_fn)(XtAppContext, Display *, _Xconst _XtString, _Xconst _XtString, XrmOptionDescRec *, Cardinal, int *, _XtString *);
void XtDisplayInitialize(XtAppContext app_context, Display *display, _Xconst _XtString application_name,
                         _Xconst _XtString application_class, XrmOptionDescRec *options, Cardinal num_options,
                         int *argc, _XtString *argv) {
    real_XtDisplayInitialize_fn real_fn = (real_XtDisplayInitialize_fn)dlsym(RTLD_NEXT, "XtDisplayInitialize");
    if (!real_fn) {
        tap_debug("could not resolve XtDisplayInitialize: %s", dlerror());
        return;
    }
    real_fn(app_context, display, application_name, application_class, options, num_options, argc, argv);
    tap_install_hooks_for_display(display);
}

typedef void (*real_XtRealizeWidget_fn)(Widget);
void XtRealizeWidget(Widget widget) {
    real_XtRealizeWidget_fn real_fn = (real_XtRealizeWidget_fn)dlsym(RTLD_NEXT, "XtRealizeWidget");
    if (!real_fn) {
        tap_debug("could not resolve XtRealizeWidget: %s", dlerror());
        return;
    }
    real_fn(widget);
    if (widget) tap_install_hooks_for_display(XtDisplay(widget));
    tap_note_widget(widget);
}

typedef void (*real_XtManageChild_fn)(Widget);
void XtManageChild(Widget child) {
    real_XtManageChild_fn real_fn = (real_XtManageChild_fn)dlsym(RTLD_NEXT, "XtManageChild");
    if (!real_fn) {
        tap_debug("could not resolve XtManageChild: %s", dlerror());
        return;
    }
    real_fn(child);
    tap_note_widget(child);
}

typedef void (*real_XtUnmanageChild_fn)(Widget);
void XtUnmanageChild(Widget child) {
    real_XtUnmanageChild_fn real_fn = (real_XtUnmanageChild_fn)dlsym(RTLD_NEXT, "XtUnmanageChild");
    if (!real_fn) {
        tap_debug("could not resolve XtUnmanageChild: %s", dlerror());
        return;
    }
    real_fn(child);
    tap_note_widget(child);
}

typedef void (*real_XtConfigureWidget_fn)(Widget, Position, Position, Dimension, Dimension, Dimension);
void XtConfigureWidget(Widget w, Position x, Position y, Dimension width, Dimension height, Dimension border_width) {
    real_XtConfigureWidget_fn real_fn = (real_XtConfigureWidget_fn)dlsym(RTLD_NEXT, "XtConfigureWidget");
    if (!real_fn) {
        tap_debug("could not resolve XtConfigureWidget: %s", dlerror());
        return;
    }
    real_fn(w, x, y, width, height, border_width);
    tap_note_widget(w);
}

typedef void (*real_XtMoveWidget_fn)(Widget, Position, Position);
void XtMoveWidget(Widget w, Position x, Position y) {
    real_XtMoveWidget_fn real_fn = (real_XtMoveWidget_fn)dlsym(RTLD_NEXT, "XtMoveWidget");
    if (!real_fn) {
        tap_debug("could not resolve XtMoveWidget: %s", dlerror());
        return;
    }
    real_fn(w, x, y);
    tap_note_widget(w);
}

typedef void (*real_XtResizeWidget_fn)(Widget, Dimension, Dimension, Dimension);
void XtResizeWidget(Widget w, Dimension width, Dimension height, Dimension border_width) {
    real_XtResizeWidget_fn real_fn = (real_XtResizeWidget_fn)dlsym(RTLD_NEXT, "XtResizeWidget");
    if (!real_fn) {
        tap_debug("could not resolve XtResizeWidget: %s", dlerror());
        return;
    }
    real_fn(w, width, height, border_width);
    tap_note_widget(w);
}

typedef void (*real_XtSetValues_fn)(Widget, ArgList, Cardinal);
void XtSetValues(Widget w, ArgList args, Cardinal num_args) {
    real_XtSetValues_fn real_fn = (real_XtSetValues_fn)dlsym(RTLD_NEXT, "XtSetValues");
    if (!real_fn) {
        tap_debug("could not resolve XtSetValues: %s", dlerror());
        return;
    }
    real_fn(w, args, num_args);
    tap_note_widget(w);
}

typedef void (*real_XtAppMainLoop_fn)(XtAppContext);
void XtAppMainLoop(XtAppContext app_context) {
    real_XtAppMainLoop_fn real_fn = (real_XtAppMainLoop_fn)dlsym(RTLD_NEXT, "XtAppMainLoop");
    if (!real_fn) {
        tap_debug("could not resolve XtAppMainLoop: %s", dlerror());
        return;
    }
    tap_dump_state();
    real_fn(app_context);
}

#ifdef MOTIF_TAP_SELF_TEST
static int tap_self_test_duplicate_paths(void) {
    CoreClassRec child_class;
    CoreClassRec root_class;
    CompositeRec root;
    CoreRec child0;
    CoreRec child1;
    Widget children[2];
    char path[TAP_PATH_MAX];

    memset(&child_class, 0, sizeof(child_class));
    memset(&root_class, 0, sizeof(root_class));
    memset(&root, 0, sizeof(root));
    memset(&child0, 0, sizeof(child0));
    memset(&child1, 0, sizeof(child1));

    child_class.core_class.class_name = "XmPushButton";
    child_class.core_class.class_inited = 0x04;
    root_class.core_class.class_name = "XmForm";
    root_class.core_class.class_inited = 0x08;

    root.core.self = (Widget)&root;
    root.core.widget_class = (WidgetClass)&root_class;
    root.core.name = "app";
    root.core.xrm_name = XrmStringToName("app");
    root.composite.children = children;
    root.composite.num_children = 2;

    child0.core.self = (Widget)&child0;
    child0.core.widget_class = (WidgetClass)&child_class;
    child0.core.parent = (Widget)&root;
    child0.core.name = "button";
    child0.core.xrm_name = XrmStringToName("button");

    child1.core.self = (Widget)&child1;
    child1.core.widget_class = (WidgetClass)&child_class;
    child1.core.parent = (Widget)&root;
    child1.core.name = "button";
    child1.core.xrm_name = XrmStringToName("button");

    children[0] = (Widget)&child0;
    children[1] = (Widget)&child1;

    tap_build_path((Widget)&child0, path, sizeof(path));
    if (strcmp(path, "app.button[0]") != 0) {
        fprintf(stderr, "expected app.button[0], got %s\n", path);
        return 1;
    }

    tap_build_path((Widget)&child1, path, sizeof(path));
    if (strcmp(path, "app.button[1]") != 0) {
        fprintf(stderr, "expected app.button[1], got %s\n", path);
        return 1;
    }

    child1.core.name = "otherButton";
    child1.core.xrm_name = XrmStringToName("otherButton");
    tap_build_path((Widget)&child0, path, sizeof(path));
    if (strcmp(path, "app.button") != 0) {
        fprintf(stderr, "expected app.button for unique path, got %s\n", path);
        return 1;
    }

    return 0;
}

int main(void) {
    return tap_self_test_duplicate_paths();
}
#endif
