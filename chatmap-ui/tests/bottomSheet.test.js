import { expect, test as it } from 'vitest'

import { CLOSED, isModal, settle, snapHeights, stepFrom } from '../src/components/BottomSheet/sheet';
import { mapTabs } from '../src/components/TabBar/tabs';

const heights = snapHeights(700);

// snapHeights
it('should make a sheet peek a strip, fill half its room or all of it', () => {
  expect(snapHeights(700, ["peek", "half", "full"], 120)).toEqual({ peek: 120, half: 350, full: 700 });
});
it('should only give the snap points the sheet uses', () => {
  expect(snapHeights(700, ["half", "full"])).toEqual({ half: 350, full: 700 });
});
it('should never peek more than the room there is', () => {
  expect(snapHeights(80, ["peek"], 120)).toEqual({ peek: 80 });
});

// settle
it('should rest a slow drag at the nearest snap point', () => {
  expect(settle({ heights, from: "half", shown: 600, velocity: 0 })).toBe("full");
  expect(settle({ heights, from: "half", shown: 400, velocity: 0 })).toBe("half");
  expect(settle({ heights, from: "half", shown: 200, velocity: 0 })).toBe("peek");
});
it('should close a sheet dragged down past its peek', () => {
  expect(settle({ heights, from: "peek", shown: 40, velocity: 0 })).toBe(CLOSED);
});
it('should not close a sheet that cannot be closed', () => {
  expect(settle({ heights, from: "peek", shown: 0, velocity: 2, closable: false })).toBe("peek");
});
it('should move a quick short flick one snap point in its direction', () => {
  expect(settle({ heights, from: "half", shown: 360, velocity: -0.6 })).toBe("full");
  expect(settle({ heights, from: "half", shown: 340, velocity: 0.6 })).toBe("peek");
  expect(settle({ heights, from: "peek", shown: 110, velocity: 0.6 })).toBe(CLOSED);
});
it('should carry a fast drag on with its speed', () => {
  // Let go at 500 px going down at 1 px/ms: it would end 150 px lower, at half
  expect(settle({ heights, from: "full", shown: 500, velocity: 1 })).toBe("half");
  // At 2 px/ms it would end 300 px lower, nearer peek
  expect(settle({ heights, from: "full", shown: 500, velocity: 2 })).toBe("peek");
});
it('should keep a flick against the end at that end', () => {
  expect(settle({ heights, from: "full", shown: 700, velocity: -3 })).toBe("full");
});

// stepFrom
it('should step one snap point up or down', () => {
  expect(stepFrom(["peek", "half", "full"], "half", 1)).toBe("full");
  expect(stepFrom(["peek", "half", "full"], "half", -1)).toBe("peek");
  expect(stepFrom(["peek", "half", "full"], "full", 1)).toBe("full");
});
it('should close stepping down from the lowest, when it can be closed', () => {
  expect(stepFrom(["half", "full"], "half", -1)).toBe(CLOSED);
  expect(stepFrom(["half", "full"], "half", -1, false)).toBe("half");
});

// dragged

// isModal
it('should be modal from the snap point asked', () => {
  const snaps = ["peek", "half", "full"];
  expect(isModal(snaps, "full")).toBe(true);
  expect(isModal(snaps, "half")).toBe(false);
  expect(isModal(snaps, "half", "half")).toBe(true);
  expect(isModal(snaps, "peek", "half")).toBe(false);
});
it('should not be modal when it never reaches that snap point', () => {
  expect(isModal(["peek", "half"], "half", "full")).toBe(false);
});

// mapTabs
it('should give a map with messages a tab for the map and one for them', () => {
  expect(mapTabs({ mapId: "m-1", withMessages: true, path: "/map/m-1/messages" })).toEqual([
    { id: "map", path: "/map/m-1", icon: "map", active: false },
    { id: "messages", path: "/map/m-1/messages", icon: "chat-square-text", active: true },
  ]);
});
it('should give no tab bar to a map without messages, nor without a map', () => {
  expect(mapTabs({ mapId: "m-1", withMessages: false, path: "/map/m-1" })).toEqual([]);
  expect(mapTabs({ mapId: undefined, withMessages: true, path: "/" })).toEqual([]);
});
