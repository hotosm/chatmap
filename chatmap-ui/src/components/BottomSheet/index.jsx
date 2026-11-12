import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { useIntl } from "react-intl";

import SlIconButton from "@shoelace-style/shoelace/dist/react/icon-button/index.js";

import { CLOSED, SNAPS, dragged, isModal, settle, snapHeights, stepFrom } from "./sheet.js";
import "./bottomSheet.css";

// What can take the focus inside the sheet, to keep it there while it is modal
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), '
    + 'textarea:not([disabled]), [tabindex]:not([tabindex="-1"]), sl-button:not([disabled]), '
    + 'sl-icon-button:not([disabled]), sl-input:not([disabled])';
// A press that moves less than this (px) is a tap, not a drag
const TAP = 4;

/**
 * A sheet that comes up from the bottom of the screen, for phones. It rests
 * at snap points (peek, half, full) and is resized by dragging its handle or
 * its title, or with the up and down arrows on the handle; dragged down, with
 * its close button or with Escape it closes. Peeking it leaves the map behind
 * it usable; from `modalAt` up it is modal: a scrim covers the rest and the
 * focus stays inside. Only its content scrolls. It sits above the tab bar
 * when there is one (--bottomSheet-bottom, see TabBar).
 *
 * @param {boolean} open Whether it is shown
 * @param {function} onClose Called when it is asked to close (button, Escape, drag down, scrim)
 * @param {node} title Its title, at the top; it also names the dialog
 * @param {string} label Names the dialog when it has no title
 * @param {string[]} snaps The snap points it uses, some of "peek", "half", "full"
 * @param {string} initialSnap The snap point it opens at
 * @param {string} snap The snap point, to control it from outside (with onSnapChange)
 * @param {function} onSnapChange Called with the snap point it moves to
 * @param {string} modalAt The lowest snap point at which it is modal ("full" by default)
 * @param {boolean} closable Whether it can be closed by the user (false: it never goes below its lowest snap point)
 * @param {number} peek The pixels in sight when it peeks
 * @param {string} className Added to the sheet
 */
export default function BottomSheet({
    open,
    onClose,
    title,
    label,
    snaps = SNAPS,
    initialSnap = "half",
    snap,
    onSnapChange,
    modalAt = "full",
    closable = true,
    peek = 120,
    className = "",
    children,
}) {
    const intl = useIntl();
    const titleId = useId();
    const sheetRef = useRef(null);
    const roomRef = useRef(null);
    const drag = useRef(null);
    const draggedLast = useRef(false);
    const [ownSnap, setOwnSnap] = useState(initialSnap);
    const [room, setRoom] = useState(0);
    const [dragShown, setDragShown] = useState(null);

    const current = snap ?? ownSnap;
    const heights = snapHeights(room, snaps, peek);
    const modal = isModal(snaps, current, modalAt);

    // It opens again at its first snap point
    useEffect(() => {
        if (open) setOwnSnap(initialSnap);
    }, [open]);

    // The room it has: what an invisible rail with its same top and bottom measures
    useLayoutEffect(() => {
        if (!open || !roomRef.current) return;
        const measure = () => setRoom(roomRef.current ? roomRef.current.clientHeight : 0);
        measure();
        const observer = new ResizeObserver(measure);
        observer.observe(roomRef.current);
        return () => observer.disconnect();
    }, [open]);

    // The focus goes into it when it opens, and back where it was when it closes
    useEffect(() => {
        if (!open) return;
        const before = document.activeElement;
        sheetRef.current && sheetRef.current.focus({ preventScroll: true });
        return () => {
            if (before && before.isConnected && before.focus) before.focus({ preventScroll: true });
        };
    }, [open]);

    if (!open) return null;

    const moveTo = (next) => {
        if (next === CLOSED) {
            onClose && onClose();
            return;
        }
        if (snap === undefined) setOwnSnap(next);
        onSnapChange && onSnapChange(next);
    };

    const onPointerDown = (event) => {
        if (event.button !== 0) return;
        // The close button and other controls in the title are pressed, not dragged
        if (event.target.closest("a, input, sl-icon-button, sl-button, button:not(.bottomSheet__handle)")) return;
        event.currentTarget.setPointerCapture(event.pointerId);
        const now = performance.now();
        drag.current = {
            id: event.pointerId, startY: event.clientY, start: heights[current] || 0,
            lastY: event.clientY, lastT: now, velocity: 0, moved: false,
        };
    };

    const onPointerMove = (event) => {
        const state = drag.current;
        if (!state || state.id !== event.pointerId) return;
        const now = performance.now();
        if (now > state.lastT) state.velocity = (event.clientY - state.lastY) / (now - state.lastT);
        state.lastY = event.clientY;
        state.lastT = now;
        if (Math.abs(event.clientY - state.startY) >= TAP) state.moved = true;
        if (state.moved) setDragShown(dragged(state.start, event.clientY - state.startY, room));
    };

    const onPointerEnd = (event) => {
        const state = drag.current;
        if (!state || state.id !== event.pointerId) return;
        drag.current = null;
        draggedLast.current = state.moved;
        if (!state.moved) return;
        const shown = dragged(state.start, event.clientY - state.startY, room);
        setDragShown(null);
        moveTo(settle({ heights, from: current, shown, velocity: state.velocity, closable }));
    };

    // A tap on the handle takes it one snap point up, and from the top back to the lowest
    const onHandleClick = () => {
        if (draggedLast.current) {
            draggedLast.current = false;
            return;
        }
        const up = stepFrom(snaps, current, 1, closable);
        moveTo(up === current ? SNAPS.find((item) => snaps.includes(item)) : up);
    };

    const onHandleKeyDown = (event) => {
        if (event.key === "ArrowUp" || event.key === "ArrowDown") {
            event.preventDefault();
            moveTo(stepFrom(snaps, current, event.key === "ArrowUp" ? 1 : -1, closable));
        }
    };

    const onKeyDown = (event) => {
        if (event.key === "Escape") {
            event.stopPropagation();
            moveTo(closable ? CLOSED : stepFrom(snaps, current, -1, false));
            return;
        }
        // While modal, Tab goes round the controls of the sheet
        if (event.key === "Tab" && modal) {
            const items = [...sheetRef.current.querySelectorAll(FOCUSABLE)];
            if (items.length === 0) return;
            const first = items[0];
            const last = items[items.length - 1];
            const active = document.activeElement;
            if (event.shiftKey && (active === first || active === sheetRef.current)) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && active === last) {
                event.preventDefault();
                first.focus();
            }
        }
    };

    const shown = dragShown ?? heights[current] ?? 0;
    const closeLabel = intl.formatMessage({ id: "app.sheet.close", defaultMessage: "Close" });

    return (
        <>
            <div className="bottomSheet__room" ref={roomRef} aria-hidden="true" />
            { modal && <div className="bottomSheet__scrim" onClick={() => closable && moveTo(CLOSED)} /> }
            <section
                ref={sheetRef}
                className={`bottomSheet ${className}`}
                role="dialog"
                aria-modal={modal ? "true" : undefined}
                aria-labelledby={title ? titleId : undefined}
                aria-label={title ? undefined : label}
                tabIndex={-1}
                data-snap={current}
                data-dragging={dragShown !== null ? "" : undefined}
                style={{ height: `${shown}px`, visibility: room ? undefined : "hidden" }}
                onKeyDown={onKeyDown}
            >
                <div
                    className="bottomSheet__drag"
                    onPointerDown={onPointerDown}
                    onPointerMove={onPointerMove}
                    onPointerUp={onPointerEnd}
                    onPointerCancel={onPointerEnd}
                >
                    <button
                        type="button"
                        className="bottomSheet__handle"
                        aria-label={intl.formatMessage({
                            id: "app.sheet.resize",
                            defaultMessage: "Resize: drag it, or use the up and down arrows",
                        })}
                        onClick={onHandleClick}
                        onKeyDown={onHandleKeyDown}
                    />
                    { (title || closable) &&
                    <div className="bottomSheet__head">
                        { title && <h2 id={titleId} className="bottomSheet__title">{title}</h2> }
                        { closable &&
                        <SlIconButton
                            className="bottomSheet__close"
                            name="x-lg"
                            label={closeLabel}
                            onClick={() => moveTo(CLOSED)}
                        /> }
                    </div> }
                </div>
                <div className="bottomSheet__body">
                    {children}
                </div>
            </section>
        </>
    );
}
