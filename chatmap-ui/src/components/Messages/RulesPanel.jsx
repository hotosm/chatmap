import { useMemo, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import SlSpinner from "@shoelace-style/shoelace/dist/react/spinner/index.js";

import { linkableKeys } from "../Tags";
import RuleCard from "./RuleCard.jsx";
import RuleForm from "./RuleForm.jsx";
import { copyOf, newRule, ruleExamples, toSend } from "./rules.js";
import useRules from "./useRules.js";

// What is being written: a new rule, or the id of the one being edited
const NEW = "new";

/**
 * The rules of a map, in the place of its messages: each one to turn on or
 * off, edit, duplicate or remove, and a new one on top; without rules,
 * examples to start from. Every rule a message meets applies, in no order;
 * they are for what the words of the options and the names of the places do
 * not say. They only suggest: a person confirms.
 *
 * @param {object} mapData The map, with its points and keys
 * @param {array} groups The groups the map listens to
 * @param {function} onBack Goes back to the messages
 */
export default function RulesPanel({ mapData, groups, onBack }) {
    const intl = useIntl();
    const { rules, failed, create, update, remove } = useRules(mapData.id);
    const [writing, setWriting] = useState(null);
    // How a new rule starts: empty, or from an example
    const [draft, setDraft] = useState(null);
    const text = (id, defaultMessage) => intl.formatMessage({ id, defaultMessage });
    const [busy, setBusy] = useState(false);
    const [notSaved, setNotSaved] = useState(false);
    // A rule suggests values of the keys with a list
    const keys = useMemo(() => linkableKeys(mapData.keys).filter(({ key }) => key.closed), [mapData.keys]);

    const nameOf = useMemo(() => ({
        group: (id) => (groups.find((group) => group.id === id) || {}).name,
        place: (id) => {
            const feature = (mapData.features || []).find((item) => item.properties.id === id);
            return feature ? feature.properties.message : "";
        },
        value: (keyId, valueId) => {
            const key = (mapData.keys || []).find((item) => item.id === keyId);
            return (key && key.values.find((item) => item.id === valueId)) || { value: "" };
        },
    }), [groups, mapData]);

    const run = async (call) => {
        setBusy(true);
        const saved = await call();
        setBusy(false);
        setNotSaved(!saved);
        return saved;
    };

    const save = async (rule) => {
        const saved = writing === NEW ? await create(toSend(rule)) : await update(writing, toSend(rule));
        if (saved) setWriting(null);
        return saved;
    };

    const form = (rule) =>
        <RuleForm
            rule={rule}
            mapData={mapData}
            groups={groups}
            keys={keys}
            onSave={save}
            onCancel={() => setWriting(null)}
        />;

    const examples = useMemo(() => ruleExamples({
        place: text("app.rules.examplePlace", "red gate, red door"),
        closed: text("app.rules.exampleClosed", "closed, shut, blocked, no way through"),
        open: text("app.rules.exampleOpen", "opened, open again"),
        greetings: text("app.rules.exampleGreetings", "good morning, hello everyone, thanks"),
        closedPlace: text("app.rules.exampleClosedPlace", "A place that closes"),
        fromGroup: text("app.rules.exampleFromGroup", "What a group says"),
        hideGreetings: text("app.rules.exampleHideGreetings", "Hide greetings"),
    }), [intl]);
    const EXAMPLE_HELP = {
        closed: text("app.rules.exampleClosedHelp", "It names the place and says it is closed, and not that it opened again."),
        group: text("app.rules.exampleFromGroupHelp", "Everything a group says about one place, when it says closed."),
        greetings: text("app.rules.exampleGreetingsHelp", "Greetings and thanks go to Dismissed, so the rest stands out."),
    };

    const start = (rule) => {
        setDraft(rule);
        setWriting(NEW);
    };

    return (
        <>
            <div className="messagesInbox__toolbar rulesPanel__bar">
                <button type="button" className="rulesPanel__back" onClick={onBack}>
                    <SlIcon name="arrow-left" />
                    <FormattedMessage id="app.messages.title" defaultMessage="Messages" />
                </button>
                { writing === null && rules &&
                    <button type="button" className="pill pill--on" onClick={() => start(newRule())}>
                        <SlIcon name="plus-lg" />
                        <FormattedMessage id="app.rules.new" defaultMessage="New rule" />
                    </button>
                }
            </div>

            <section className="messagesInbox__messages rulesPanel">
                <header className="rulesPanel__header">
                    <h2 className="rulesPanel__title">
                        <FormattedMessage id="app.rules.title" defaultMessage="Rules" />
                    </h2>
                    <p className="rulesPanel__help">
                        <FormattedMessage
                            id="app.rules.help"
                            defaultMessage="For what the words of each status and the names of each place do not cover. Every rule a message meets applies, in no order, and the messages nobody answered are read again when you save. They only suggest: a person confirms."
                        />
                    </p>
                </header>

                { writing === NEW && form(draft) }

                { rules === null && <SlSpinner className="messagesInbox__loading" /> }
                { failed &&
                    <p className="messagesInbox__error" role="alert">
                        <FormattedMessage id="app.rules.notRead" defaultMessage="The rules could not be read. Try again." />
                    </p>
                }

                { rules && rules.length === 0 && writing !== NEW && !failed &&
                    <div className="rulesPanel__start">
                        <p className="rulesPanel__startTitle">
                            <FormattedMessage id="app.rules.none" defaultMessage="This map has no rules yet." />
                        </p>
                        <p className="rulesPanel__help">
                            <FormattedMessage id="app.rules.startFrom" defaultMessage="Start from one of these and adjust it to your places:" />
                        </p>
                        <ul className="rulesPanel__examples">
                            { examples.map((example) =>
                                <li key={example.id}>
                                    <button type="button" className="rulesPanel__example" onClick={() => start(example.rule)}>
                                        <strong>{example.rule.description}</strong>
                                        <span>{EXAMPLE_HELP[example.id]}</span>
                                    </button>
                                </li>
                            )}
                        </ul>
                    </div>
                }

                { rules && rules.map((rule) => writing === rule.id ?
                    <div key={rule.id}>{form(rule)}</div> :
                    <RuleCard
                        key={rule.id}
                        rule={rule}
                        nameOf={nameOf}
                        busy={busy}
                        onToggle={() => run(() => update(rule.id, { ...toSend(rule), enabled: !rule.enabled }))}
                        onEdit={() => setWriting(rule.id)}
                        onCopy={() => run(() => create(copyOf(rule, text("app.rules.copySuffix", "(copy)"))))}
                        onRemove={() => run(() => remove(rule.id))}
                    />
                )}

                { notSaved &&
                    <p className="messagesInbox__error" role="alert">
                        <FormattedMessage id="app.messages.notSaved" defaultMessage="It could not be saved. Try again." />
                    </p>
                }
            </section>
        </>
    );
}
