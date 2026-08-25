import { useNavigate, useParams } from "react-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import Header from "../header.jsx";
import Footer from "../footer.jsx";
import { FormattedMessage, useIntl } from "react-intl";

import SlSwitch from "@shoelace-style/shoelace/dist/react/switch/index.js";
import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import useAPI from '../../components/ChatMap/useApi.js';
import EditBotItemDialog from '../../components/EditBotItemDialog/index.jsx';
import MaxAttemptsDialog from '../../components/MaxAttemptsDialog/index.jsx';
import {
  END_STEP, FIXED_STEPS, QUESTION_ICON,
  emptyQuestion, maxAttemptsFromSetup, maxAttemptsHasProblems,
  messagesFromSetup, messagesToSave, problemsIn, questionsOf,
} from '../../utils/botSetup.js';
import '../../styles/botSetup.css';

export default function BotSetup() {
  const { id } = useParams();
  const navigate = useNavigate();
  const intl = useIntl();
  const { fetchBotSetup, updateBotSetup, isLoading, error } = useAPI();

  const [botActive, setBotActive] = useState(false);
  // Starts as the empty form so the steps are on screen from the first paint,
  // even if the request never comes back
  const [messages, setMessages] = useState(() => messagesFromSetup(null));
  const [maxAttempts, setMaxAttempts] = useState(() => maxAttemptsFromSetup(null));
  const [editing, setEditing] = useState(null);
  const [showMaxAttempts, setShowMaxAttempts] = useState(false);
  const [invalid, setInvalid] = useState(false);

  useEffect(() => {
    async function fetchData() {
      const setup = await fetchBotSetup(id);
      if (setup) {
        setBotActive(setup.bot_active);
        setMessages(messagesFromSetup(setup));
        setMaxAttempts(maxAttemptsFromSetup(setup));
      }
    }
    fetchData();
  }, [id]);

  const labels = useMemo(() => ({
    start: intl.formatMessage({ id: "app.botSetup.startMessage", defaultMessage: "Start message" }),
    media: intl.formatMessage({ id: "app.botSetup.media", defaultMessage: "Media" }),
    location: intl.formatMessage({ id: "app.botSetup.location", defaultMessage: "Location" }),
    end: intl.formatMessage({ id: "app.botSetup.endMessage", defaultMessage: "End message" }),
    single_choice: intl.formatMessage({ id: "app.botSetup.singleChoice", defaultMessage: "Single choice" }),
  }), [intl]);

  // Marked rows are the ones that block the save; recomputed as the user edits
  // so a fixed row stops being marked without saving again
  const problems = useMemo(() => problemsIn(messages, botActive), [messages, botActive]);
  const maxAttemptsInvalid = useMemo(
    () => maxAttemptsHasProblems(maxAttempts, botActive), [maxAttempts, botActive]
  );

  const questions = questionsOf(messages);
  const questionKey = (question) => question.id || `new-question-${questions.indexOf(question)}`;

  const updateMessage = useCallback((target, changes) => {
    setMessages((current) => current.map((message) => (message === target ? { ...message, ...changes } : message)));
  }, []);

  function openEditor(message, editingError, label, icon) {
    setEditing({ message, editingError, label, icon });
  }

  function addQuestion() {
    setMessages([...messages, emptyQuestion(questions.length)]);
  }

  function removeQuestion(question) {
    setMessages(messages.filter((message) => message !== question));
  }

  async function handleSave() {
    if (problems.size > 0 || maxAttemptsInvalid) {
      setInvalid(true);
      // That section is behind a button, so marking it is useless while it is
      // collapsed
      if (maxAttemptsInvalid) setShowMaxAttempts(true);
      return;
    }
    setInvalid(false);

    const saved = await updateBotSetup(id, {
      bot_active: botActive,
      messages: messagesToSave(messages),
      max_attempts_messages: maxAttempts,
    });
    if (saved) {
      navigate("/maps");
    }
  }

  function renderRow(message, definition, label) {
    const marked = invalid && problems.has(message.bot_step === "single_choice" ? questionKey(message) : message.bot_step);

    return (
      <div className="botSetup__row" key={message.bot_step === "single_choice" ? questionKey(message) : message.bot_step}>
        <div className={`botSetup__item ${marked ? "botSetup__item--invalid" : ""}`}>
          <SlIcon name={definition.icon} />
          <span className={message.prompt ? "" : "botSetup__item-empty"}>
            {message.prompt || label}
          </span>
          <div className="botSetup__item-actions">
            { message.bot_step === "single_choice" &&
            <button
              type="button"
              className="botSetup__icon-button"
              title={intl.formatMessage({ id: "app.botSetup.removeQuestion", defaultMessage: "Remove question" })}
              onClick={() => removeQuestion(message)}
            >
              <SlIcon name="dash-circle" />
            </button>
            }
            <button
              type="button"
              className="botSetup__icon-button"
              title={intl.formatMessage({ id: "app.botSetup.edit", defaultMessage: "Edit" })}
              onClick={() => openEditor(message, false, label, definition.icon)}
            >
              <SlIcon name="pencil" />
            </button>
          </div>
        </div>

        { definition.answers &&
        <div className={`botSetup__item botSetup__item--error ${marked ? "botSetup__item--invalid" : ""}`}>
          <SlIcon name="chat-square-text" />
          <span className={message.error_message ? "" : "botSetup__item-empty"}>
            {message.error_message || intl.formatMessage({
              id: "app.botSetup.incorrectAnswer", defaultMessage: "Incorrect answer",
            })}
          </span>
          <div className="botSetup__item-actions">
            <button
              type="button"
              className="botSetup__icon-button"
              title={intl.formatMessage({ id: "app.botSetup.edit", defaultMessage: "Edit" })}
              onClick={() => openEditor(message, true, label, definition.icon)}
            >
              <SlIcon name="pencil" />
            </button>
          </div>
        </div>
        }
      </div>
    );
  }

  function rowFor(definition) {
    const message = messages.find((candidate) => candidate.bot_step === definition.bot_step);
    return message ? renderRow(message, definition, labels[definition.bot_step]) : null;
  }

  return (
    <>
      <div className="app">
        <Header pageTitle={"Bot Setup"} />

        <div className="botSetup">
          <div className="botSetup__header">
            <div className="botSetup__header-left">
              <h1>
                <SlIcon name="robot" />
                <FormattedMessage id="app.botSetup.title" defaultMessage="Bot setup" />
              </h1>
            </div>
          </div>

          <div className="botSetup__content">
            {/* Error alerts */}
            <sl-alert open={error ? true : false} variant="primary" duration="3000" closable>
                <sl-icon slot="icon" name="info-circle"></sl-icon>
                <strong>Something went wrong</strong><br />
                {error}
            </sl-alert>

            { invalid &&
            <div className="error error-box">
              <FormattedMessage
                id="app.botSetup.incompleteError"
                defaultMessage="Fill in the highlighted messages before saving."
              />
            </div>
            }

            <SlSwitch
              size="small"
              checked={botActive}
              disabled={isLoading}
              onSlChange={(event) => setBotActive(event.target.checked)}
            >
              <FormattedMessage
                id="app.botSetup.enable"
                defaultMessage="Enable bot mode for this device"
              />
            </SlSwitch>

            <div className="botSetup__items">
              { FIXED_STEPS.map(rowFor) }

              { questions.map((question) => renderRow(
                question, { bot_step: "single_choice", icon: QUESTION_ICON, answers: true }, labels.single_choice
              )) }

              <button type="button" className="botSetup__item botSetup__item--add" onClick={addQuestion}>
                <SlIcon name={QUESTION_ICON} />
                <span className="botSetup__item-empty">{labels.single_choice}</span>
                <div className="botSetup__item-actions">
                  <SlIcon name="plus-circle" />
                </div>
              </button>

              { rowFor(END_STEP) }
            </div>

            <button
              type="button"
              className={`botSetup__item ${invalid && maxAttemptsInvalid ? "botSetup__item--invalid" : ""}`}
              onClick={() => setShowMaxAttempts(true)}
            >
              <SlIcon name="arrow-clockwise" />
              <span>
                <FormattedMessage
                  id="app.botSetup.maxAttemptsMessages"
                  defaultMessage="Cancel or restart messages"
                />
              </span>
            </button>
          </div>

          <div className="botSetup__divider"></div>

          <div className="botSetup__form_buttons">
            <SlButton variant="default" outline onClick={() => navigate("/maps")}>
              <FormattedMessage id="app.botSetup.cancel" defaultMessage="Cancel" />
            </SlButton>
            <SlButton variant="primary" loading={isLoading} onClick={handleSave}>
              <FormattedMessage id="app.botSetup.save" defaultMessage="Save changes" />
            </SlButton>
          </div>
        </div>

        <Footer />
      </div>

      <EditBotItemDialog
        open={editing !== null}
        setOpen={(open) => !open && setEditing(null)}
        message={editing?.message}
        editingError={editing?.editingError}
        label={editing?.label}
        icon={editing?.icon}
        onSave={(changes) => updateMessage(editing.message, changes)}
      />

      <MaxAttemptsDialog
        open={showMaxAttempts}
        setOpen={setShowMaxAttempts}
        maxAttempts={maxAttempts}
        onSave={(changes) => setMaxAttempts({ ...maxAttempts, ...changes })}
      />
    </>
  )
}
