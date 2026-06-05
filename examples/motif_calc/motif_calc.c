#include <Xm/Form.h>
#include <Xm/Label.h>
#include <Xm/PushB.h>
#include <Xm/RowColumn.h>
#include <Xm/Xm.h>
#include <X11/keysym.h>

#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define RESULT_DIR "/tmp/motif-calc"
#define RESULT_FILE "/tmp/motif-calc/result.txt"
#define DISPLAY_MAX 64

typedef struct {
    Widget display;
    char input[DISPLAY_MAX];
    double accumulator;
    char pending_op;
    int start_new_input;
    int error;
} CalcState;

typedef enum {
    CALC_BUTTON_DIGIT,
    CALC_BUTTON_OPERATOR,
    CALC_BUTTON_EQUALS,
    CALC_BUTTON_CLEAR
} CalcButtonKind;

typedef struct {
    Widget widget;
    CalcButtonKind kind;
} CalcButtonRef;

typedef struct {
    CalcState *state;
    CalcButtonRef buttons[16];
    int button_count;
} CalcUi;

static void set_display(CalcState *state, const char *text) {
    XmString value = XmStringCreateLocalized((char *)text);
    XtVaSetValues(state->display, XmNlabelString, value, NULL);
    XmStringFree(value);
}

static void ensure_result_dir(void) {
    if (mkdir(RESULT_DIR, 0777) != 0 && errno != EEXIST) {
        perror("mkdir " RESULT_DIR);
    }
}

static void write_result(const char *text) {
    ensure_result_dir();
    FILE *file = fopen(RESULT_FILE, "w");
    if (!file) {
        perror("fopen " RESULT_FILE);
        return;
    }
    fputs(text, file);
    fputc('\n', file);
    fclose(file);
}

static void format_number(double value, char *out, size_t out_size) {
    double rounded = round(value);
    if (fabs(value - rounded) < 0.0000001) {
        snprintf(out, out_size, "%.0f", rounded);
    } else {
        snprintf(out, out_size, "%.8g", value);
    }
}

static void clear_state(CalcState *state) {
    strcpy(state->input, "0");
    state->accumulator = 0.0;
    state->pending_op = '\0';
    state->start_new_input = 1;
    state->error = 0;
    set_display(state, state->input);
    write_result(state->input);
}

static int apply_pending(CalcState *state, double rhs) {
    switch (state->pending_op) {
        case '+':
            state->accumulator += rhs;
            return 1;
        case '-':
            state->accumulator -= rhs;
            return 1;
        case '*':
            state->accumulator *= rhs;
            return 1;
        case '/':
            if (fabs(rhs) < 0.0000001) {
                state->error = 1;
                strcpy(state->input, "ERR");
                set_display(state, state->input);
                write_result(state->input);
                return 0;
            }
            state->accumulator /= rhs;
            return 1;
        default:
            state->accumulator = rhs;
            return 1;
    }
}

static void digit_cb(Widget widget, XtPointer client_data, XtPointer call_data) {
    (void)widget;
    (void)call_data;
    CalcState *state = (CalcState *)client_data;
    const char *name = XtName(widget);
    char digit = name[strlen(name) - 1];

    if (state->error || state->start_new_input || strcmp(state->input, "0") == 0) {
        state->input[0] = digit;
        state->input[1] = '\0';
        state->start_new_input = 0;
        state->error = 0;
    } else {
        size_t len = strlen(state->input);
        if (len + 1 < sizeof(state->input)) {
            state->input[len] = digit;
            state->input[len + 1] = '\0';
        }
    }

    set_display(state, state->input);
}

static void operator_cb(Widget widget, XtPointer client_data, XtPointer call_data) {
    (void)call_data;
    CalcState *state = (CalcState *)client_data;
    const char *name = XtName(widget);
    double rhs = atof(state->input);

    if (!state->start_new_input && !apply_pending(state, rhs)) {
        return;
    }

    if (strcmp(name, "addButton") == 0) {
        state->pending_op = '+';
    } else if (strcmp(name, "subtractButton") == 0) {
        state->pending_op = '-';
    } else if (strcmp(name, "multiplyButton") == 0) {
        state->pending_op = '*';
    } else if (strcmp(name, "divideButton") == 0) {
        state->pending_op = '/';
    }

    format_number(state->accumulator, state->input, sizeof(state->input));
    set_display(state, state->input);
    state->start_new_input = 1;
}

static void equals_cb(Widget widget, XtPointer client_data, XtPointer call_data) {
    (void)widget;
    (void)call_data;
    CalcState *state = (CalcState *)client_data;
    double rhs = atof(state->input);

    if (state->error || !apply_pending(state, rhs)) {
        return;
    }

    state->pending_op = '\0';
    format_number(state->accumulator, state->input, sizeof(state->input));
    set_display(state, state->input);
    write_result(state->input);
    state->start_new_input = 1;
}

static void clear_cb(Widget widget, XtPointer client_data, XtPointer call_data) {
    (void)widget;
    (void)call_data;
    clear_state((CalcState *)client_data);
}

static Widget make_button(
    Widget parent,
    const char *name,
    const char *label,
    XtCallbackProc callback,
    CalcState *state
) {
    XmString text = XmStringCreateLocalized((char *)label);
    Widget button = XtVaCreateManagedWidget(
        name,
        xmPushButtonWidgetClass,
        parent,
        XmNlabelString,
        text,
        NULL
    );
    XmStringFree(text);
    XtAddCallback(button, XmNactivateCallback, callback, state);
    return button;
}

static void add_button_ref(CalcUi *ui, Widget widget, CalcButtonKind kind) {
    if (ui->button_count < (int)(sizeof(ui->buttons) / sizeof(ui->buttons[0]))) {
        ui->buttons[ui->button_count].widget = widget;
        ui->buttons[ui->button_count].kind = kind;
        ui->button_count++;
    }
}

static void dispatch_button_ref(CalcButtonRef *button, CalcState *state) {
    switch (button->kind) {
        case CALC_BUTTON_DIGIT:
            digit_cb(button->widget, state, NULL);
            break;
        case CALC_BUTTON_OPERATOR:
            operator_cb(button->widget, state, NULL);
            break;
        case CALC_BUTTON_EQUALS:
            equals_cb(button->widget, state, NULL);
            break;
        case CALC_BUTTON_CLEAR:
            clear_cb(button->widget, state, NULL);
            break;
    }
}

static CalcButtonRef *find_button_by_name(CalcUi *ui, const char *name) {
    if (!ui || !name) {
        return NULL;
    }

    for (int i = 0; i < ui->button_count; ++i) {
        const char *button_name = XtName(ui->buttons[i].widget);
        if (button_name && strcmp(button_name, name) == 0) {
            return &ui->buttons[i];
        }
    }

    return NULL;
}

static void dispatch_button_name(CalcUi *ui, const char *name) {
    CalcButtonRef *button = find_button_by_name(ui, name);
    if (button) {
        dispatch_button_ref(button, ui->state);
    }
}

static void calculator_key_press_cb(
    Widget widget,
    XtPointer client_data,
    XEvent *event,
    Boolean *continue_to_dispatch
) {
    (void)widget;

    if (!event || event->type != KeyPress) {
        return;
    }

    CalcUi *ui = (CalcUi *)client_data;
    if (!ui || !ui->state) {
        return;
    }

    KeySym keysym = XLookupKeysym(&event->xkey, 0);
    if (keysym >= XK_0 && keysym <= XK_9) {
        char name[] = "digit0";
        name[5] = (char)('0' + (keysym - XK_0));
        dispatch_button_name(ui, name);
    } else if (keysym >= XK_KP_0 && keysym <= XK_KP_9) {
        char name[] = "digit0";
        name[5] = (char)('0' + (keysym - XK_KP_0));
        dispatch_button_name(ui, name);
    } else if (keysym == XK_asterisk || keysym == XK_KP_Multiply) {
        dispatch_button_name(ui, "multiplyButton");
    } else if (keysym == XK_plus || keysym == XK_KP_Add) {
        dispatch_button_name(ui, "addButton");
    } else if (keysym == XK_minus || keysym == XK_KP_Subtract) {
        dispatch_button_name(ui, "subtractButton");
    } else if (keysym == XK_slash || keysym == XK_KP_Divide) {
        dispatch_button_name(ui, "divideButton");
    } else if (keysym == XK_Return || keysym == XK_KP_Enter || keysym == XK_equal) {
        dispatch_button_name(ui, "equalsButton");
    } else if (keysym == XK_Escape || keysym == XK_c || keysym == XK_C) {
        dispatch_button_name(ui, "clearButton");
    } else {
        return;
    }

    if (continue_to_dispatch) {
        *continue_to_dispatch = False;
    }
}

static int widget_xy_relative_to(Widget child, Widget ancestor, Position *out_x, Position *out_y) {
    Position total_x = 0;
    Position total_y = 0;

    for (Widget current = child; current; current = XtParent(current)) {
        if (current == ancestor) {
            *out_x = total_x;
            *out_y = total_y;
            return 1;
        }

        Position x = 0;
        Position y = 0;
        XtVaGetValues(current, XmNx, &x, XmNy, &y, NULL);
        total_x += x;
        total_y += y;
    }

    return 0;
}

static void keypad_button_release_cb(
    Widget widget,
    XtPointer client_data,
    XEvent *event,
    Boolean *continue_to_dispatch
) {
    (void)widget;
    (void)continue_to_dispatch;

    if (!event || event->type != ButtonRelease || event->xbutton.button != Button1) {
        return;
    }

    CalcUi *ui = (CalcUi *)client_data;
    if (!ui || !ui->state) {
        return;
    }

    for (int i = 0; i < ui->button_count; ++i) {
        CalcButtonRef *button = &ui->buttons[i];
        Position x = 0;
        Position y = 0;
        Dimension width = 0;
        Dimension height = 0;
        XtVaGetValues(
            button->widget,
            XmNwidth,
            &width,
            XmNheight,
            &height,
            NULL
        );
        if (!widget_xy_relative_to(button->widget, widget, &x, &y)) {
            continue;
        }

        if (
            event->xbutton.x >= x &&
            event->xbutton.x < x + (Position)width &&
            event->xbutton.y >= y &&
            event->xbutton.y < y + (Position)height
        ) {
            dispatch_button_ref(button, ui->state);
            if (continue_to_dispatch) {
                *continue_to_dispatch = False;
            }
            return;
        }
    }
}

int main(int argc, char **argv) {
    XtAppContext app;
    Widget shell = XtVaAppInitialize(
        &app,
        "MotifCalc",
        NULL,
        0,
        &argc,
        argv,
        NULL,
        XmNtitle,
        "Motif Calculator",
        XmNwidth,
        400,
        XmNheight,
        320,
        NULL
    );

    Widget form = XtVaCreateManagedWidget("calculatorForm", xmFormWidgetClass, shell, NULL);

    XmString initial = XmStringCreateLocalized("0");
    Widget display = XtVaCreateManagedWidget(
        "displayLabel",
        xmLabelWidgetClass,
        form,
        XmNlabelString,
        initial,
        XmNtopAttachment,
        XmATTACH_FORM,
        XmNleftAttachment,
        XmATTACH_FORM,
        XmNrightAttachment,
        XmATTACH_FORM,
        XmNmarginWidth,
        16,
        XmNmarginHeight,
        12,
        NULL
    );
    XmStringFree(initial);

    Widget keypad = XtVaCreateManagedWidget(
        "keypad",
        xmRowColumnWidgetClass,
        form,
        XmNtopAttachment,
        XmATTACH_WIDGET,
        XmNtopWidget,
        display,
        XmNleftAttachment,
        XmATTACH_FORM,
        XmNrightAttachment,
        XmATTACH_FORM,
        XmNbottomAttachment,
        XmATTACH_FORM,
        XmNpacking,
        XmPACK_COLUMN,
        XmNnumColumns,
        4,
        XmNorientation,
        XmVERTICAL,
        NULL
    );

    CalcState state;
    memset(&state, 0, sizeof(state));
    state.display = display;
    clear_state(&state);

    CalcUi ui;
    memset(&ui, 0, sizeof(ui));
    ui.state = &state;

    add_button_ref(&ui, make_button(keypad, "digit7", "7", digit_cb, &state), CALC_BUTTON_DIGIT);
    add_button_ref(&ui, make_button(keypad, "digit8", "8", digit_cb, &state), CALC_BUTTON_DIGIT);
    add_button_ref(&ui, make_button(keypad, "digit9", "9", digit_cb, &state), CALC_BUTTON_DIGIT);
    add_button_ref(&ui, make_button(keypad, "divideButton", "/", operator_cb, &state), CALC_BUTTON_OPERATOR);

    add_button_ref(&ui, make_button(keypad, "digit4", "4", digit_cb, &state), CALC_BUTTON_DIGIT);
    add_button_ref(&ui, make_button(keypad, "digit5", "5", digit_cb, &state), CALC_BUTTON_DIGIT);
    add_button_ref(&ui, make_button(keypad, "digit6", "6", digit_cb, &state), CALC_BUTTON_DIGIT);
    add_button_ref(&ui, make_button(keypad, "multiplyButton", "*", operator_cb, &state), CALC_BUTTON_OPERATOR);

    add_button_ref(&ui, make_button(keypad, "digit1", "1", digit_cb, &state), CALC_BUTTON_DIGIT);
    add_button_ref(&ui, make_button(keypad, "digit2", "2", digit_cb, &state), CALC_BUTTON_DIGIT);
    add_button_ref(&ui, make_button(keypad, "digit3", "3", digit_cb, &state), CALC_BUTTON_DIGIT);
    add_button_ref(&ui, make_button(keypad, "subtractButton", "-", operator_cb, &state), CALC_BUTTON_OPERATOR);

    add_button_ref(&ui, make_button(keypad, "clearButton", "C", clear_cb, &state), CALC_BUTTON_CLEAR);
    add_button_ref(&ui, make_button(keypad, "digit0", "0", digit_cb, &state), CALC_BUTTON_DIGIT);
    add_button_ref(&ui, make_button(keypad, "equalsButton", "=", equals_cb, &state), CALC_BUTTON_EQUALS);
    add_button_ref(&ui, make_button(keypad, "addButton", "+", operator_cb, &state), CALC_BUTTON_OPERATOR);

    XtAddEventHandler(shell, ButtonReleaseMask, False, keypad_button_release_cb, &ui);
    XtAddEventHandler(form, ButtonReleaseMask, False, keypad_button_release_cb, &ui);
    XtAddEventHandler(keypad, ButtonReleaseMask, False, keypad_button_release_cb, &ui);
    XtAddEventHandler(shell, KeyPressMask, False, calculator_key_press_cb, &ui);
    XtAddEventHandler(form, KeyPressMask, False, calculator_key_press_cb, &ui);
    XtAddEventHandler(keypad, KeyPressMask, False, calculator_key_press_cb, &ui);

    XtRealizeWidget(shell);
    XtSetKeyboardFocus(shell, form);
    XtAppMainLoop(app);
    return 0;
}
