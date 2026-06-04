#include <Xm/Form.h>
#include <Xm/Label.h>
#include <Xm/PushB.h>
#include <Xm/RowColumn.h>
#include <Xm/Xm.h>

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

    make_button(keypad, "digit7", "7", digit_cb, &state);
    make_button(keypad, "digit8", "8", digit_cb, &state);
    make_button(keypad, "digit9", "9", digit_cb, &state);
    make_button(keypad, "divideButton", "/", operator_cb, &state);

    make_button(keypad, "digit4", "4", digit_cb, &state);
    make_button(keypad, "digit5", "5", digit_cb, &state);
    make_button(keypad, "digit6", "6", digit_cb, &state);
    make_button(keypad, "multiplyButton", "*", operator_cb, &state);

    make_button(keypad, "digit1", "1", digit_cb, &state);
    make_button(keypad, "digit2", "2", digit_cb, &state);
    make_button(keypad, "digit3", "3", digit_cb, &state);
    make_button(keypad, "subtractButton", "-", operator_cb, &state);

    make_button(keypad, "clearButton", "C", clear_cb, &state);
    make_button(keypad, "digit0", "0", digit_cb, &state);
    make_button(keypad, "equalsButton", "=", equals_cb, &state);
    make_button(keypad, "addButton", "+", operator_cb, &state);

    XtRealizeWidget(shell);
    XtAppMainLoop(app);
    return 0;
}
