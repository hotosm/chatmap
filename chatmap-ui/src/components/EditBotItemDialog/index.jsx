import {useEffect, useState} from "react";
import {FormattedMessage, useIntl} from "react-intl";

import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlTextarea from "@shoelace-style/shoelace/dist/react/textarea/index.js";
import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";

import {MAX_OPTIONS, MIN_OPTIONS, isQuestion} from "../../utils/botSetup.js";

export default function EditBotItemDialog({
                                              open, setOpen, message, editingError, label, icon, onSave
                                          }) {
    const intl = useIntl();

    const [text, setText] = useState("");
    const [options, setOptions] = useState([]);

    // Reopening on a different message has to start from that message's own values
    useEffect(() => {
        if (!open || !message) return;
        setText((editingError ? message.error_message : message.prompt) || "");
        setOptions(editingError ? [] : [...(message.options || [])]);
    }, [open, message, editingError]);

    if (!message) return null;

    const editsOptions = !editingError && message.bot_step === "single_choice";

    function handleOptionChange(index, value) {
        setOptions(options.map((option, i) => (i === index ? value : option)));
    }

    function handleSave() {
        onSave(editingError
            ? {error_message: text}
            : {prompt: text, ...(editsOptions ? {options} : {})});
        setOpen(false);
    }

    return (
        <SlDialog open={open} onSlAfterHide={() => setOpen(false)}>
            <h2 slot="label" className="dialog__title">
                <FormattedMessage id="app.botSetup.editItem" defaultMessage="Edit conversation item"/>
            </h2>

            <div className="botSetup__dialog-kind">
                <SlIcon name={icon}/>
                <span>{label}</span>
            </div>

            <SlTextarea
                className="botSetup__dialog-text"
                rows="3"
                resize="auto"
                value={text}
                placeholder={editingError
                    ? intl.formatMessage({
                        id: "app.botSetup.incorrectAnswerPlaceholder",
                        defaultMessage: "What the bot replies when the answer is not valid",
                    })
                    : isQuestion(message.bot_step)
                        ? intl.formatMessage({
                            id: "app.botSetup.questionPlaceholder",
                            defaultMessage: "The question the bot asks",
                        })
                        : intl.formatMessage({
                            id: "app.botSetup.messagePlaceholder",
                            defaultMessage: "What the bot sends at this step",
                        })}
                onSlInput={(event) => setText(event.target.value)}
            />

            {editsOptions && <div className="botSetup__options">
                {options.map((option, index) => (
                    <div className="botSetup__option" key={index}>
                        <SlInput
                            value={option}
                            placeholder={intl.formatMessage({
                                id: "app.botSetup.optionPlaceholder",
                                defaultMessage: "Answer the user can pick",
                            })}
                            onSlInput={(event) => handleOptionChange(index, event.target.value)}
                        />
                        <SlButton
                            variant="default"
                            outline
                            disabled={options.length <= MIN_OPTIONS}
                            onClick={() => setOptions(options.filter((_, i) => i !== index))}
                        >
                            <SlIcon name="dash-circle" slot="prefix"/>
                        </SlButton>
                    </div>
                ))}

                {options.length < MAX_OPTIONS &&
                    <SlButton
                        className="botSetup__add"
                        variant="default"
                        outline
                        onClick={() => setOptions([...options, ""])}
                    >
                        <FormattedMessage id="app.botSetup.addOption" defaultMessage="Add option"/>
                        <SlIcon name="plus-circle" slot="suffix"/>
                    </SlButton>
                }
            </div>}

            <div slot="footer" className="botSetup__dialog-buttons">
                <SlButton variant="default" outline onClick={() => setOpen(false)}>
                    <FormattedMessage id="app.botSetup.cancel" defaultMessage="Cancel"/>
                </SlButton>
                <SlButton variant="primary" onClick={handleSave}>
                    <FormattedMessage id="app.botSetup.save" defaultMessage="Save changes"/>
                </SlButton>
            </div>
        </SlDialog>
    );
};
