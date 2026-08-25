export const MIN_OPTIONS = 2;
export const MAX_OPTIONS = 10;

export const FIXED_STEPS = [
    {bot_step: "start", icon: "chat-square-text", answers: false},
    {bot_step: "media", icon: "camera", answers: true},
    {bot_step: "location", icon: "pin-map", answers: true},
];

export const END_STEP = {bot_step: "end", icon: "chat-square-text", answers: false};

export const QUESTION_ICON = "list-ul";

const REQUIRED_STEPS = ["start", "media", "location", "end"];
const STEPS_NEEDING_AN_ERROR = ["media", "location"];

function filled(text) {
    return Boolean((text || "").trim());
}

export function emptyMessage(botStep) {
    return {
        id: null,
        bot_step: botStep,
        position: null,
        prompt: "",
        error_message: STEPS_NEEDING_AN_ERROR.includes(botStep) ? "" : null,
        options: [],
    };
}

export function emptyQuestion(position) {
    return {
        id: null,
        bot_step: "single_choice",
        position,
        prompt: "",
        error_message: "",
        options: ["", ""],
    };
}

export function emptyMaxAttemptsMessages() {
    return {id: null, max_attempts_quantity: 3, notify_message: "", to_restart: "", to_cancel: ""};
}

export function messageOf(messages, botStep) {
    return messages.find((message) => message.bot_step === botStep);
}

export function questionsOf(messages) {
    return messages.filter((message) => message.bot_step === "single_choice");
}

export function problemsIn(messages, botActive) {
    const problems = new Set();

    questionsOf(messages).forEach((question, index) => {
        const key = question.id || `new-question-${index}`;
        const options = (question.options || []).filter(filled);
        if (!filled(question.prompt) || !filled(question.error_message)
            || options.length < MIN_OPTIONS || options.length > MAX_OPTIONS) {
            problems.add(key);
        }
    });

    if (!botActive) return problems;

    REQUIRED_STEPS.forEach((botStep) => {
        const message = messageOf(messages, botStep);
        if (!message || !filled(message.prompt)) problems.add(botStep);
    });

    STEPS_NEEDING_AN_ERROR.forEach((botStep) => {
        const message = messageOf(messages, botStep);
        if (message && !filled(message.error_message)) problems.add(botStep);
    });

    return problems;
}

export function maxAttemptsHasProblems(maxAttempts, botActive) {
    if (!botActive) return false;
    return !filled(maxAttempts.notify_message)
        || !filled(maxAttempts.to_restart)
        || !filled(maxAttempts.to_cancel)
        || !(Number(maxAttempts.max_attempts_quantity) >= 1);
}

export function messagesFromSetup(setup) {
    const stored = setup?.messages || [];
    const fixed = [...FIXED_STEPS, END_STEP].map(
        ({bot_step}) => stored.find((message) => message.bot_step === bot_step) || emptyMessage(bot_step)
    );
    const questions = questionsOf(stored)
        .slice()
        .sort((a, b) => (a.position ?? 0) - (b.position ?? 0));

    return [...fixed, ...questions];
}

export function maxAttemptsFromSetup(setup) {
    return setup?.max_attempts_messages
        ? {...emptyMaxAttemptsMessages(), ...setup.max_attempts_messages}
        : emptyMaxAttemptsMessages();
}

export function messagesToSave(messages) {
    let questionPosition = 0;

    return messages
        .filter((message) => filled(message.prompt)
            || filled(message.error_message)
            || (message.options || []).some(filled))
        .map((message) => ({
            ...message,
            position: message.bot_step === "single_choice" ? questionPosition++ : null,
        }));
}
