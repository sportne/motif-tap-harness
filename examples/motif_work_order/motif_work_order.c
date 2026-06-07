#include <Xm/CascadeB.h>
#include <Xm/Form.h>
#include <Xm/Label.h>
#include <Xm/MainW.h>
#include <Xm/Notebook.h>
#include <Xm/PushB.h>
#include <Xm/RowColumn.h>
#include <Xm/TextF.h>
#include <Xm/ToggleB.h>
#include <Xm/Xm.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define RESULT_DIR "/tmp/motif-work-order"
#define RESULT_FILE "/tmp/motif-work-order/result.txt"
#define SERVICE_MAX 32

typedef struct {
    Widget customer_field;
    Widget rush_toggle;
    Widget quantity_field;
    Widget inspection_toggle;
    Widget calibration_toggle;
    char service[SERVICE_MAX];
} WorkOrderState;

typedef struct {
    Widget notebook;
    int page_number;
} TabTarget;

static XmString make_string(const char *text) {
    return XmStringCreateLocalized((char *)text);
}

static void set_label(Widget widget, const char *text) {
    XmString label = make_string(text);
    XtVaSetValues(widget, XmNlabelString, label, NULL);
    XmStringFree(label);
}

static Widget make_label(Widget parent, const char *name, const char *text) {
    XmString label = make_string(text);
    Widget widget = XtVaCreateManagedWidget(
        name,
        xmLabelWidgetClass,
        parent,
        XmNlabelString,
        label,
        XmNalignment,
        XmALIGNMENT_BEGINNING,
        NULL
    );
    XmStringFree(label);
    return widget;
}

static Widget make_button(Widget parent, const char *name, const char *text) {
    XmString label = make_string(text);
    Widget widget = XtVaCreateManagedWidget(
        name,
        xmPushButtonWidgetClass,
        parent,
        XmNlabelString,
        label,
        NULL
    );
    XmStringFree(label);
    return widget;
}

static void ensure_result_dir(void) {
    if (mkdir(RESULT_DIR, 0777) != 0 && errno != EEXIST) {
        perror("mkdir " RESULT_DIR);
    }
}

static void write_result(WorkOrderState *state, const char *submitted_via) {
    char *customer = XmTextFieldGetString(state->customer_field);
    char *quantity = XmTextFieldGetString(state->quantity_field);
    Boolean rush = XmToggleButtonGetState(state->rush_toggle);

    ensure_result_dir();
    FILE *file = fopen(RESULT_FILE, "w");
    if (!file) {
        perror("fopen " RESULT_FILE);
        XtFree(customer);
        XtFree(quantity);
        return;
    }

    fprintf(file, "customer=%s\n", customer && *customer ? customer : "");
    fprintf(file, "service=%s\n", state->service);
    fprintf(file, "rush=%s\n", rush ? "true" : "false");
    fprintf(file, "quantity=%s\n", quantity && *quantity ? quantity : "");
    fprintf(file, "submitted_via=%s\n", submitted_via);
    fclose(file);

    XtFree(customer);
    XtFree(quantity);
}

static void reset_state(WorkOrderState *state) {
    XmTextFieldSetString(state->customer_field, "");
    XmTextFieldSetString(state->quantity_field, "");
    XmToggleButtonSetState(state->rush_toggle, False, False);
    XmToggleButtonSetState(state->inspection_toggle, False, False);
    XmToggleButtonSetState(state->calibration_toggle, True, False);
    strcpy(state->service, "calibration");
}

static void submit_cb(Widget widget, XtPointer client_data, XtPointer call_data) {
    (void)widget;
    (void)call_data;
    write_result((WorkOrderState *)client_data, "menu");
}

static void reset_cb(Widget widget, XtPointer client_data, XtPointer call_data) {
    (void)widget;
    (void)call_data;
    reset_state((WorkOrderState *)client_data);
}

static void service_cb(Widget widget, XtPointer client_data, XtPointer call_data) {
    WorkOrderState *state = (WorkOrderState *)client_data;
    XmToggleButtonCallbackStruct *toggle = (XmToggleButtonCallbackStruct *)call_data;
    if (!toggle || !toggle->set) {
        return;
    }

    if (widget == state->calibration_toggle) {
        strcpy(state->service, "calibration");
        XmToggleButtonSetState(state->inspection_toggle, False, False);
    } else {
        strcpy(state->service, "inspection");
        XmToggleButtonSetState(state->calibration_toggle, False, False);
    }
}

static void service_release_cb(
    Widget widget,
    XtPointer client_data,
    XEvent *event,
    Boolean *continue_to_dispatch
) {
    (void)continue_to_dispatch;
    if (!event || (event->type != ButtonPress && event->type != ButtonRelease)) {
        return;
    }

    WorkOrderState *state = (WorkOrderState *)client_data;
    if (widget == state->calibration_toggle) {
        strcpy(state->service, "calibration");
        XmToggleButtonSetState(state->calibration_toggle, True, False);
        XmToggleButtonSetState(state->inspection_toggle, False, False);
    } else if (widget == state->inspection_toggle) {
        strcpy(state->service, "inspection");
        XmToggleButtonSetState(state->inspection_toggle, True, False);
        XmToggleButtonSetState(state->calibration_toggle, False, False);
    }
}

static void tab_cb(Widget widget, XtPointer client_data, XtPointer call_data) {
    (void)widget;
    (void)call_data;
    TabTarget *target = (TabTarget *)client_data;
    XtVaSetValues(target->notebook, XmNcurrentPageNumber, target->page_number, NULL);
}

static Widget make_menu_bar(Widget parent, WorkOrderState *state) {
    Widget menu_bar = XmCreateMenuBar(parent, "menuBar", NULL, 0);
    Widget file_menu = XmCreatePulldownMenu(menu_bar, "fileMenu", NULL, 0);

    XmString file_label = make_string("File");
    XtVaCreateManagedWidget(
        "fileMenuButton",
        xmCascadeButtonWidgetClass,
        menu_bar,
        XmNlabelString,
        file_label,
        XmNsubMenuId,
        file_menu,
        XmNmnemonic,
        'F',
        NULL
    );
    XmStringFree(file_label);

    Widget reset_item = make_button(file_menu, "resetMenuItem", "Reset");
    Widget submit_item = make_button(file_menu, "submitMenuItem", "Submit Work Order");
    XtVaSetValues(reset_item, XmNmnemonic, 'R', NULL);
    XtVaSetValues(submit_item, XmNmnemonic, 'S', NULL);
    XtAddCallback(reset_item, XmNactivateCallback, reset_cb, state);
    XtAddCallback(submit_item, XmNactivateCallback, submit_cb, state);
    XtManageChild(menu_bar);
    return menu_bar;
}

static Widget make_customer_page(Widget notebook, WorkOrderState *state) {
    Widget page = XtVaCreateManagedWidget(
        "customerPage",
        xmFormWidgetClass,
        notebook,
        XmNnotebookChildType,
        XmPAGE,
        XmNpageNumber,
        1,
        NULL
    );

    Widget name_label = make_label(page, "customerNameLabel", "Customer name");
    XtVaSetValues(
        name_label,
        XmNtopAttachment,
        XmATTACH_FORM,
        XmNleftAttachment,
        XmATTACH_FORM,
        XmNtopOffset,
        16,
        XmNleftOffset,
        16,
        NULL
    );

    state->customer_field = XtVaCreateManagedWidget(
        "customerNameField",
        xmTextFieldWidgetClass,
        page,
        XmNtopAttachment,
        XmATTACH_WIDGET,
        XmNtopWidget,
        name_label,
        XmNleftAttachment,
        XmATTACH_FORM,
        XmNrightAttachment,
        XmATTACH_FORM,
        XmNtopOffset,
        8,
        XmNleftOffset,
        16,
        XmNrightOffset,
        16,
        NULL
    );

    state->rush_toggle = XtVaCreateManagedWidget(
        "rushToggle",
        xmToggleButtonWidgetClass,
        page,
        XmNtopAttachment,
        XmATTACH_WIDGET,
        XmNtopWidget,
        state->customer_field,
        XmNleftAttachment,
        XmATTACH_FORM,
        XmNtopOffset,
        18,
        XmNleftOffset,
        16,
        NULL
    );
    set_label(state->rush_toggle, "Rush order");
    return page;
}

static Widget make_details_page(Widget notebook, WorkOrderState *state) {
    Widget page = XtVaCreateManagedWidget(
        "detailsPage",
        xmFormWidgetClass,
        notebook,
        XmNnotebookChildType,
        XmPAGE,
        XmNpageNumber,
        2,
        NULL
    );

    Widget service_label = make_label(page, "serviceTypeLabel", "Service type");
    XtVaSetValues(
        service_label,
        XmNtopAttachment,
        XmATTACH_FORM,
        XmNleftAttachment,
        XmATTACH_FORM,
        XmNtopOffset,
        16,
        XmNleftOffset,
        16,
        NULL
    );

    Widget service_box = XtVaCreateManagedWidget(
        "serviceTypeBox",
        xmRowColumnWidgetClass,
        page,
        XmNtopAttachment,
        XmATTACH_WIDGET,
        XmNtopWidget,
        service_label,
        XmNleftAttachment,
        XmATTACH_FORM,
        XmNtopOffset,
        8,
        XmNleftOffset,
        16,
        XmNorientation,
        XmHORIZONTAL,
        XmNradioBehavior,
        True,
        NULL
    );

    state->inspection_toggle = XtVaCreateManagedWidget(
        "inspectionToggle",
        xmToggleButtonWidgetClass,
        service_box,
        XmNset,
        False,
        NULL
    );
    set_label(state->inspection_toggle, "Inspection");
    state->calibration_toggle =
        XtVaCreateManagedWidget("calibrationToggle", xmToggleButtonWidgetClass, service_box, NULL);
    set_label(state->calibration_toggle, "Calibration");
    XtAddCallback(state->inspection_toggle, XmNvalueChangedCallback, service_cb, state);
    XtAddCallback(state->calibration_toggle, XmNvalueChangedCallback, service_cb, state);
    XtAddEventHandler(
        state->inspection_toggle,
        ButtonPressMask | ButtonReleaseMask,
        False,
        service_release_cb,
        state
    );
    XtAddEventHandler(
        state->calibration_toggle,
        ButtonPressMask | ButtonReleaseMask,
        False,
        service_release_cb,
        state
    );

    Widget quantity_label = make_label(page, "quantityLabel", "Quantity");
    XtVaSetValues(
        quantity_label,
        XmNtopAttachment,
        XmATTACH_WIDGET,
        XmNtopWidget,
        service_box,
        XmNleftAttachment,
        XmATTACH_FORM,
        XmNtopOffset,
        18,
        XmNleftOffset,
        16,
        NULL
    );

    state->quantity_field = XtVaCreateManagedWidget(
        "quantityField",
        xmTextFieldWidgetClass,
        page,
        XmNtopAttachment,
        XmATTACH_WIDGET,
        XmNtopWidget,
        quantity_label,
        XmNleftAttachment,
        XmATTACH_FORM,
        XmNtopOffset,
        8,
        XmNleftOffset,
        16,
        XmNcolumns,
        8,
        NULL
    );
    return page;
}

static Widget make_notebook(Widget parent, WorkOrderState *state) {
    Widget notebook = XtVaCreateManagedWidget(
        "workOrderNotebook",
        xmNotebookWidgetClass,
        parent,
        XmNwidth,
        520,
        XmNheight,
        320,
        NULL
    );

    make_customer_page(notebook, state);
    make_details_page(notebook, state);

    Widget customer_tab = make_button(notebook, "customerTab", "Customer");
    static TabTarget customer_target;
    customer_target.notebook = notebook;
    customer_target.page_number = 1;
    XtVaSetValues(
        customer_tab,
        XmNnotebookChildType,
        XmMAJOR_TAB,
        XmNpageNumber,
        1,
        NULL
    );
    XtAddCallback(customer_tab, XmNactivateCallback, tab_cb, &customer_target);

    Widget details_tab = make_button(notebook, "detailsTab", "Details");
    static TabTarget details_target;
    details_target.notebook = notebook;
    details_target.page_number = 2;
    XtVaSetValues(
        details_tab,
        XmNnotebookChildType,
        XmMAJOR_TAB,
        XmNpageNumber,
        2,
        NULL
    );
    XtAddCallback(details_tab, XmNactivateCallback, tab_cb, &details_target);
    return notebook;
}

int main(int argc, char **argv) {
    XtAppContext app;
    Widget shell = XtVaAppInitialize(
        &app,
        "WorkOrderDesk",
        NULL,
        0,
        &argc,
        argv,
        NULL,
        XmNtitle,
        "Work Order Desk",
        XmNwidth,
        560,
        XmNheight,
        400,
        XmNkeyboardFocusPolicy,
        XmPOINTER,
        NULL
    );

    WorkOrderState state;
    memset(&state, 0, sizeof(state));
    strcpy(state.service, "calibration");

    Widget main_window = XtVaCreateManagedWidget(
        "workOrderMainWindow",
        xmMainWindowWidgetClass,
        shell,
        NULL
    );
    Widget menu_bar = make_menu_bar(main_window, &state);
    Widget notebook = make_notebook(main_window, &state);
    XmMainWindowSetAreas(main_window, menu_bar, NULL, NULL, NULL, notebook);

    XtRealizeWidget(shell);
    reset_state(&state);
    XtAppMainLoop(app);
    return 0;
}
