import { useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import useGroupName from "./useGroupName.js";
import useMessagesApi from "./useMessagesApi.js";

// How many days the messages can be kept, to pick from
const DAYS = [7, 15, 30, 60, 90];

/**
 * The groups of the phone of a live map, in a panel under a pill. Its owner
 * chooses the ones the map listens to: only their messages are kept, from
 * then on, and only for as many days as it says. Stopping one is confirmed
 * right there, keeping its messages until they expire or removing them now.
 *
 * @param {object} phone The groups and days as the API answers them
 * @param {function} onChange Gets the groups and days after a change
 */
export default function GroupsPicker({ mapId, phone, onChange }) {
    const intl = useIntl();
    const { updateGroup, updateKeptDays } = useMessagesApi();
    const [stopping, setStopping] = useState(null);
    const [busy, setBusy] = useState(false);
    const [failed, setFailed] = useState(false);

    async function run(call, apply) {
        setBusy(true);
        const saved = await call();
        setBusy(false);
        setFailed(!saved);
        if (saved) onChange(apply(saved));
        return saved;
    }

    const setGroup = (group, change) => run(
        () => updateGroup(mapId, group.id, change),
        (saved) => ({ ...phone, groups: phone.groups.map((item) => item.id === saved.id ? saved : item) }),
    ).then((saved) => saved && setStopping(null));

    const setDays = (days) => run(() => updateKeptDays(mapId, days), (saved) => ({ ...phone, kept_days: saved.days }));

    const days = [...new Set([...DAYS, phone.kept_days])]
        .filter((value) => value <= phone.max_kept_days)
        .sort((a, b) => a - b);
    const groupName = useGroupName();

    return (
        <sl-dropdown className="groupsPicker" placement="bottom-start" hoist>
            <button slot="trigger" type="button" className="pill pill--outline pill--caret">
                <FormattedMessage id="app.messages.chooseGroups" defaultMessage="Choose groups" />
            </button>

            <div className="popoverPanel groupsPicker__panel">
                <h3 className="groupsPicker__title">
                    <FormattedMessage id="app.messages.groupsTitle" defaultMessage="Groups of the phone" />
                </h3>
                <p className="groupsPicker__help">
                    <FormattedMessage
                        id="app.messages.groupsHelp"
                        defaultMessage="Only the messages of the groups you listen to are kept, from the moment you choose them."
                    />
                </p>

                { phone.failed &&
                    <p className="groupsPicker__error" role="alert">
                        <FormattedMessage id="app.messages.groupsNotRead" defaultMessage="The groups of the phone could not be read. Try again." />
                    </p>
                }
                { !phone.failed && phone.groups.length === 0 &&
                    <p className="groupsPicker__help">
                        <FormattedMessage id="app.messages.noPhoneGroups" defaultMessage="The phone linked to this map is in no group." />
                    </p>
                }

                <ul className="groupsPicker__list">
                    { phone.groups.map((group) =>
                        <li key={group.id} className="groupsPicker__item">
                            <div className="groupsPicker__row">
                                <span className={`groupsPicker__name ${group.enabled ? "groupsPicker__name--on" : ""}`}>{groupName(group.name)}</span>
                                { group.enabled ?
                                    <button
                                        type="button"
                                        className="pill pill--on"
                                        disabled={busy}
                                        aria-expanded={stopping === group.id}
                                        onClick={() => setStopping(stopping === group.id ? null : group.id)}
                                    >
                                        <SlIcon name="check-lg" />
                                        <FormattedMessage id="app.messages.listening" defaultMessage="Listening" />
                                    </button> :
                                    <button type="button" className="pill pill--outline" disabled={busy} onClick={() => setGroup(group, { enabled: true })}>
                                        <FormattedMessage id="app.messages.listen" defaultMessage="Listen" />
                                    </button>
                                }
                            </div>

                            { stopping === group.id &&
                                <div className="groupsPicker__stop">
                                    <p>
                                        <FormattedMessage
                                            id="app.messages.stopHelp"
                                            defaultMessage="Its new messages will not be kept. The ones already kept stay until they expire, unless you remove them now."
                                        />
                                    </p>
                                    <div className="groupsPicker__stopActions">
                                        <button type="button" className="pill pill--outline" disabled={busy} onClick={() => setGroup(group, { enabled: false })}>
                                            <FormattedMessage id="app.messages.stop" defaultMessage="Stop listening" />
                                        </button>
                                        <button
                                            type="button"
                                            className="pill pill--outline pill--danger"
                                            disabled={busy}
                                            onClick={() => setGroup(group, { enabled: false, delete_messages: true })}
                                        >
                                            <FormattedMessage id="app.messages.stopAndDelete" defaultMessage="Stop and remove its messages" />
                                        </button>
                                        <button type="button" className="groupsPicker__cancel" onClick={() => setStopping(null)}>
                                            <FormattedMessage id="app.dialog.confirm.cancel" defaultMessage="Cancel" />
                                        </button>
                                    </div>
                                </div>
                            }
                        </li>
                    )}
                </ul>

                { !phone.failed &&
                    <label className="groupsPicker__days">
                        <FormattedMessage id="app.messages.keptFor" defaultMessage="Keep messages for" />
                        <span className="pill pill--outline pill--caret">
                            <select
                                className="pill__select"
                                value={phone.kept_days}
                                disabled={busy}
                                onChange={(event) => setDays(Number(event.target.value))}
                            >
                                { days.map((value) =>
                                    <option key={value} value={value}>
                                        {intl.formatMessage(
                                            { id: "app.messages.days", defaultMessage: "{days, plural, one {# day} other {# days}}" },
                                            { days: value },
                                        )}
                                    </option>
                                )}
                            </select>
                        </span>
                    </label>
                }

                { failed &&
                    <p className="groupsPicker__error" role="alert">
                        <FormattedMessage id="app.messages.notSaved" defaultMessage="It could not be saved. Try again." />
                    </p>
                }
            </div>
        </sl-dropdown>
    );
}
