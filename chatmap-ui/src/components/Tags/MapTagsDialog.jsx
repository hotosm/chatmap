import { useEffect, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";

import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIconButton from "@shoelace-style/shoelace/dist/react/icon-button/index.js";

import ConfirmDialog from "../ConfirmDialog/index.jsx";
import useTagsApi from "./useTagsApi.js";
import { keepArrows } from "./tags.js";
import KeyForm from "./KeyForm.jsx";
import ValueForm, { VALUE_COLORS } from "./ValueForm.jsx";

/**
 * The tags of a map: its keys, each with its options (when it has a list),
 * and the free tags its points use. Here its owner creates keys, edits their
 * options, archives or removes them, and picks the one that colors the map.
 */
export default function MapTagsDialog({ open, setOpen, mapId, keys, inUse, freeTagsInUse, onChange }) {
  const intl = useIntl();
  const { createKey, updateKey, removeKey } = useTagsApi();

  // What is being edited: null (the list), { key } (a key) or { key, value } (one of its options)
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  // What is about to be removed, once confirmed: { name, remove }
  const [removing, setRemoving] = useState(null);

  useEffect(() => {
    if (open) {
      setEditing(null);
      setError(null);
    }
  }, [open]);

  const confirmRemove = (name, remove) => setRemoving({ name, remove });

  const active = keys.filter((key) => !key.archived);
  const archived = keys.filter((key) => key.archived);

  // Run a change, then show the keys as the API answers them
  async function run(call, errorMessage, apply) {
    setLoading(true);
    const saved = await call();
    setLoading(false);
    if (!saved) {
      setError(errorMessage);
      return;
    }
    setEditing(null);
    setError(null);
    onChange(apply(saved));
  }

  const replace = (saved) => keys.map((key) => key.id === saved.id ? saved : key);
  const notSaved = intl.formatMessage({
    id: "app.tags.notSaved",
    defaultMessage: "It could not be saved. Names cannot repeat, and an option some point has can only be archived.",
  });

  const saveKey = (key) => editing.key.id ?
    run(() => updateKey(mapId, editing.key.id, key), notSaved, replace) :
    run(() => createKey(mapId, key), notSaved, (saved) => [...keys, saved]);

  const saveValues = (key, values) => run(() => updateKey(mapId, key.id, { values }), notSaved, replace);

  function saveValue(value) {
    const { key } = editing;
    const values = value.id ?
      key.values.map((item) => item.id === value.id ? value : item) :
      [...key.values, value];
    saveValues(key, values);
  }

  // An archived key cannot color the map
  const setArchived = (key, archived) => run(
    () => updateKey(mapId, key.id, archived ? { archived, colors_map: false } : { archived }), notSaved, replace,
  );

  // Opening a form leaves the last error behind
  const edit = (editing) => {
    setError(null);
    setEditing(editing);
  };

  // Choosing a key unchooses the one that colored the map
  const colorMapBy = (key, colors) => run(
    () => updateKey(mapId, key.id, { colors_map: colors }), notSaved,
    (saved) => keys.map((item) => item.id === saved.id ? saved : { ...item, colors_map: colors ? false : item.colors_map }),
  );

  const remove = (key) => run(
    () => removeKey(mapId, key.id),
    intl.formatMessage({
      id: "app.tags.notRemoved",
      defaultMessage: "Only a tag never given to a point can be removed. Archive it instead.",
    }),
    () => keys.filter((item) => item.id !== key.id),
  );

  const title = !editing ?
    <FormattedMessage id="app.tags.mapTags" defaultMessage="Tags of the map" /> :
    editing.value ?
      (editing.value.id ?
        <FormattedMessage id="app.tags.editOption" defaultMessage="Edit option of {key}" values={{ key: editing.key.key }} /> :
        <FormattedMessage id="app.tags.newOption" defaultMessage="New option of {key}" values={{ key: editing.key.key }} />) :
      (editing.key.id ?
        <FormattedMessage id="app.tags.renameKey" defaultMessage="Rename tag" /> :
        <FormattedMessage id="app.tags.newKey" defaultMessage="New tag" />);

  return (<>
    <SlDialog
      className="tags__dialog"
      open={open}
      onKeyDown={keepArrows}
      // Only when the dialog hides: the color picker inside also tells it hid
      onSlAfterHide={(event) => event.target === event.currentTarget && setOpen(false)}
      onSlInitialFocus={(event) => {
        // Focus the close button, not the panel: browsing with caret draws a cursor there
        const close = event.target.shadowRoot && event.target.shadowRoot.querySelector('[part~="close-button"]');
        if (!close) return;
        event.preventDefault();
        close.focus();
      }}
    >
      <h2 slot="label" className="dialog__title">{title}</h2>

      { error && <div className="error error-box">{error}</div> }

      { editing && editing.value &&
        <ValueForm
          key={editing.value.id || "new"}
          value={editing.value}
          loading={loading}
          onSave={saveValue}
          onArchive={(value) => saveValue({ ...value, archived: true })}
          onCancel={() => setEditing(null)}
        />
      }
      { editing && !editing.value &&
        <KeyForm keyItem={editing.key} loading={loading} onSave={saveKey} onCancel={() => setEditing(null)} />
      }

      { !editing && <>
        <p className="tags__help">
          <FormattedMessage
            id="app.tags.help"
            defaultMessage="Tags describe each point. Create the ones you need, like a status or a category, and choose which one colors the map."
          />
        </p>

        { active.map((key) =>
          <KeySection
            key={key.id}
            keyItem={key}
            inUse={inUse}
            loading={loading}
            onAddValue={() => edit({ key, value: { color: key.single ? VALUE_COLORS[key.values.length % VALUE_COLORS.length] : null } })}
            onEditValue={(value) => edit({ key, value })}
            onRestoreValue={(value) => saveValues(key, key.values.map((item) => item.id === value.id ? { ...item, archived: false } : item))}
            onRemoveValue={(value) => confirmRemove(value.value, () => saveValues(key, key.values.filter((item) => item.id !== value.id)))}
            onRename={() => edit({ key })}
            onColorMap={(colors) => colorMapBy(key, colors)}
            onArchive={() => setArchived(key, true)}
            onRemove={() => confirmRemove(key.key, () => remove(key))}
          />
        )}

        <section className="tags__key">
          <header className="tags__keyHeader">
            <h3><FormattedMessage id="app.tags.freeTags" defaultMessage="Free tags" /></h3>
          </header>
          <p className="tags__muted tags__kind">
            <FormattedMessage id="app.tags.freeTagsKind" defaultMessage="Written on each point, without options" />
          </p>
          { freeTagsInUse.length > 0 ?
            <div className="tags__inUse">
              { freeTagsInUse.map(({ tag, count }) =>
                <span key={tag} className="pointTags__chip pointTags__chip--free tags__inUseTag">
                  {tag} <span className="tags__muted">· {count}</span>
                </span>
              )}
            </div>
          :
            <p className="tags__muted tags__empty">
              <FormattedMessage id="app.tags.freeTagsNone" defaultMessage="No point has free tags yet." />
            </p>
          }
        </section>

        { archived.length > 0 &&
          <section className="tags__key">
            <h4 className="tags__archived"><FormattedMessage id="app.tags.archived" defaultMessage="Archived" /></h4>
            <ul className="tags__values">
              { archived.map((key) =>
                <li key={key.id} className="tags__value tags__value--archived">
                  <span className="tags__valueText tags__muted">{key.key}</span>
                  <SlButton size="small" variant="text" className="tags__danger" disabled={loading} onClick={() => confirmRemove(key.key, () => remove(key))}>
                    <FormattedMessage id="app.tags.removeKey" defaultMessage="Remove" />
                  </SlButton>
                  <SlButton size="small" disabled={loading} onClick={() => setArchived(key, false)}>
                    <FormattedMessage id="app.tags.restore" defaultMessage="Restore" />
                  </SlButton>
                </li>
              )}
            </ul>
          </section>
        }

        <div className="tags__buttons">
          <SlButton variant="primary" className="dark-btn" disabled={loading} onClick={() => edit({ key: {} })}>
            <FormattedMessage id="app.tags.addKey" defaultMessage="+ New tag" />
          </SlButton>
        </div>
      </>}
    </SlDialog>

    <ConfirmDialog
      open={removing !== null}
      setOpen={(open) => !open && setRemoving(null)}
      data={removing}
      onConfirm={(confirmed) => confirmed.remove()}
      title={{
        id: "app.tags.confirmRemove",
        defaultMessage: "Remove “{name}”?",
        values: { name: removing && removing.name },
      }}
      okText={{ id: "app.tags.removeKey", defaultMessage: "Remove" }}
    >
      <FormattedMessage id="app.tags.confirmRemoveText" defaultMessage="It cannot be undone." />
    </ConfirmDialog>
  </>);
};

// What a key is, in words: "One per point · picked from options"
function kindOf(key) {
  return (
    <FormattedMessage
      id={`app.tags.kind.${key.single ? "single" : "many"}.${key.closed ? "list" : "text"}`}
      defaultMessage={{
        "single.list": "One per point · picked from options",
        "single.text": "One per point · written freely",
        "many.list": "Many per point · picked from options",
        "many.text": "Many per point · written freely",
      }[`${key.single ? "single" : "many"}.${key.closed ? "list" : "text"}`]}
    />
  );
}

function KeySection({
  keyItem, inUse, loading, onAddValue, onEditValue, onRestoreValue, onRemoveValue, onRename, onColorMap, onArchive,
  onRemove,
}) {
  const intl = useIntl();
  const values = keyItem.values.filter((value) => !value.archived);
  const archived = keyItem.values.filter((value) => value.archived);
  // Only a key with one value per point and a list can color the map
  const canColor = keyItem.single && keyItem.closed;
  const expires = (value) => value.expires_after ?
    intl.formatMessage(
      { id: "app.tags.expiresIn", defaultMessage: "Expires after {hours}" },
      { hours: intl.formatNumber(value.expires_after, { style: "unit", unit: "hour", unitDisplay: "short" }) },
    ) :
    intl.formatMessage({ id: "app.tags.expiresNot", defaultMessage: "Does not expire" });

  return (
    <section className="tags__key">
      <header className="tags__keyHeader">
        <h3>{keyItem.key}</h3>
        { keyItem.colors_map &&
          <span className="tags__badge"><FormattedMessage id="app.tags.colorsMap" defaultMessage="Colors the map" /></span>
        }
        <span className="tags__keyActions">
          { keyItem.closed &&
            <SlButton size="small" pill variant="primary" className="dark-btn" disabled={loading} onClick={onAddValue}>
              <FormattedMessage id="app.tags.addOption" defaultMessage="Add option" />
            </SlButton>
          }
          <sl-dropdown hoist>
            <SlIconButton
              slot="trigger"
              name="three-dots-vertical"
              disabled={loading}
              label={intl.formatMessage({ id: "app.tags.moreActions", defaultMessage: "More actions" })}
            />
            <sl-menu>
              <sl-menu-item onClick={onRename}>
                <FormattedMessage id="app.tags.rename" defaultMessage="Rename" />
              </sl-menu-item>
              { canColor && !keyItem.colors_map &&
                <sl-menu-item onClick={() => onColorMap(true)}>
                  <FormattedMessage id="app.tags.colorMapBy" defaultMessage="Color the map with it" />
                </sl-menu-item>
              }
              { keyItem.colors_map &&
                <sl-menu-item onClick={() => onColorMap(false)}>
                  <FormattedMessage id="app.tags.stopColoring" defaultMessage="Stop coloring the map" />
                </sl-menu-item>
              }
              <sl-menu-item onClick={onArchive}>
                <FormattedMessage id="app.tags.archive" defaultMessage="Archive" />
              </sl-menu-item>
              <sl-menu-item onClick={onRemove}>
                <FormattedMessage id="app.tags.removeKey" defaultMessage="Remove" />
              </sl-menu-item>
            </sl-menu>
          </sl-dropdown>
        </span>
      </header>
      <p className="tags__muted tags__kind">{kindOf(keyItem)}</p>

      { keyItem.closed && values.length === 0 &&
        <p className="tags__muted tags__empty">
          <FormattedMessage id="app.tags.noOptions" defaultMessage="It has no options yet." />
        </p>
      }
      <ul className="tags__values">
        { values.map((value) =>
          <li key={value.id}>
            <button className="tags__value" disabled={loading} onClick={() => onEditValue(value)}>
              <span
                className={`tags__dot ${value.color ? "" : "tags__dot--none"}`}
                style={{ backgroundColor: value.color || undefined }}
              />
              <span className="tags__valueText">
                <strong>{value.value}</strong>
                { value.description && <span className="tags__muted">{value.description}</span> }
              </span>
              <span className="tags__muted tags__expires">{expires(value)}</span>
            </button>
          </li>
        )}
      </ul>

      { archived.length > 0 && <>
        <h4 className="tags__archived"><FormattedMessage id="app.tags.archived" defaultMessage="Archived" /></h4>
        <ul className="tags__values">
          { archived.map((value) =>
            <li key={value.id} className="tags__value tags__value--archived">
              <span className="tags__dot" style={{ backgroundColor: value.color || undefined }} />
              <span className="tags__valueText tags__muted">{value.value}</span>
              {/* An option some point has can only stay archived */}
              { !inUse.has(value.id) &&
                <SlButton size="small" variant="text" className="tags__danger" disabled={loading} onClick={() => onRemoveValue(value)}>
                  <FormattedMessage id="app.tags.removeOption" defaultMessage="Remove" />
                </SlButton>
              }
              <SlButton size="small" disabled={loading} onClick={() => onRestoreValue(value)}>
                <FormattedMessage id="app.tags.restore" defaultMessage="Restore" />
              </SlButton>
            </li>
          )}
        </ul>
      </>}
    </section>
  );
}
