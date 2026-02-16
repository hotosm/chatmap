
/**
 * Contains a main parser function and supporting fuctions
 * for creating a map from a WhatsApp conversation log.
 *
 * The Map is stored in memory as a GeoJSON and a list
 * of media files
 */

import ignore from "./ignore";

// Regex to search for coordinates in the format <lat>,<lon> (ex: -31.006037,-64.262794)
const LOCATION_PATTERN = /[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?).*$/;

// Regex to search for messages in the format [<date>, <time>] <username>: <message>
const MSG_PATTERN = {
    IOS: /^\[(.*)\] ([^:]*): (.*)/,
    ANDROID: /^(.*) - ([^:]*): (.*)/
}

const HOUR_PATTERN = /(\d{1,2})[:.](\d{1,2})(:\d{1,2})?(\s+[pP])?/;

const TYPES = {
  ".jpg": "image",
  ".ogg": "audio",
  ".opus": "audio",
  ".mp3": "audio",
  ".m4a": "audio",
  ".wav": "audio",
  ".mp4": "video",
}

// Detect system (Android or iOS)
export const detectSystem = (line) => {
    const match_ios = line.match(MSG_PATTERN.IOS);
    const match_android = line.match(MSG_PATTERN.ANDROID);
    if (match_ios) {
        return "IOS";
    } else if (match_android) {
        return "ANDROID"
    }
    return "UNKNOWN";
}

// Look for jpg, mp4, or audio media files
export const lookForMediaFile = (msgObject) => {
    const msg = msgObject.message.toLowerCase();
    // Supported media extensions
    const extensions = [".jpg", ".mp4", ".ogg", ".opus", ".mp3", ".m4a", ".wav"];
    let mediaFileIndex = -1;
    let foundExt = "";
    for (let ext of extensions) {
        let idx = msg.indexOf(ext);
        if (idx > 0) {
            mediaFileIndex = idx;
            foundExt = ext;
            break;
        }
    }

    if (mediaFileIndex > 0) {
        let path = msgObject.message.substring(msg.lastIndexOf(":") + 1, mediaFileIndex + foundExt.length);

        if (path.substring(0, 1) == " ") {
            path = path.substring(1);
        }

        return {path, type: TYPES[foundExt]};
    }

    return null;
}

// Search for a location
export const searchLocation = msgObject => {
    if (msgObject.message) {
        const match = msgObject.message.match(LOCATION_PATTERN);
        if (match) {
            return match[0].split(",").map(x => parseFloat(x))
        }
    }
    return null;
}

// Check if message is in list of ignored strings
const isInTheIgnoreList = msg => {
    for (let i = 0; i < ignore.length; i++) {
        if (msg.indexOf(ignore[i]) > -1) {
            return true;
        }
    };
    return false;
}

// Parse time, username and message
const parseMessage = (line, system, getTime) => {
    const match = line.match(MSG_PATTERN[system]);

    if (match && !isInTheIgnoreList(match[3])) {
        let username = match[2];

        // Check if the username has a ':' character and remove the text after it
        const usernameIndexOf = username.indexOf(":");
        if (usernameIndexOf > -1) {
            username = username.substring(0, usernameIndexOf);
        }

        let msgObject = {
            time: getTime(line),
            username:  username,
            message: match[3],
        }

        // Look for media
        const mediaFile = lookForMediaFile(msgObject);

        if (mediaFile !== null) {
          msgObject.file = mediaFile.path;
          msgObject.file_type = mediaFile.type;
        }

        if (msgObject.file) {
            msgObject.message = "";
        }

        return msgObject;
    }
}

// Parse time strings
export const parseTimeString = (dateStr) => {
    let dateTimeStr = dateStr.replace("a. m.", "AM").replace("p. m.", "PM")
    dateTimeStr = dateTimeStr.replace("a.m.", "AM").replace("p.m.", "PM")
    let dateTime = dateTimeStr.split(" ");
    const now = new Date();
    let fmtDate = [[now.getFullYear(), now.getMonth() + 1, now.getDate()].join("/"), dateTime[1]].join(" ").replaceAll(".", ":")

    return new Date(fmtDate);
}

/**
 * Returns how many items differ between two 3-item arrays and what their
 * indices are
 */
export function howManyChanged(parts1, parts2) {
  const indices = [];

  for (let i = 0; i<3; i++) {
    if (parts1[i] !== parts2[i]) {
      indices.push(i);
    }
  }

  return indices;
}

/**
 * @returns {int[]} A three-element array with the parts of a date as numbers
 */
function getDateParts(match) {
  return match
    .split(' ')[0].replace(',', '')
    .split('/').map(Number);
}

/**
 * @returns {string[]}
 */
function getTimeParts(match) {
  const matches = match.match(HOUR_PATTERN);
  let hour = Number(matches[1]);
  const minute = Number(matches[2]);
  let second = 0;

  if ((matches[3] && matches[3].startsWith(' ')) || matches[4]) {
    hour += 12;
  } else if (matches[3] && matches[3].match(/\d+/)) {
    second = Number(matches[3].slice(1));
  }

  return [
    hour.toString().padStart(2, "0"),
    minute.toString().padStart(2, "0"),
    second.toString().padStart(2, "0"),
  ];
}

function normalizeParts(dateParts, yearIndex, monthIndex, dayIndex, match) {
  const year = (dateParts[yearIndex] < 100 ? dateParts[yearIndex] + 2000 : dateParts[yearIndex]).toString();
  const [month, day] = [dateParts[monthIndex].toString().padStart(2, "0"), dateParts[dayIndex].toString().padStart(2, "0")];
  const [hour, minute, second] = getTimeParts(match[1]);

  return [year, month, day, hour, minute, second];
}

/**
 * Returns a function that correctly parses a message's date given that no
 * transition was found in the exported file.
 */
function makeCase0Function(dateParts, system) {
  let yearIndex, monthIndex, dayIndex;

  if (dateParts[0] <= 12) {
    monthIndex = 0;
    dayIndex = 1;
    yearIndex = 2;
  } else if (dateParts[1] <= 12) {
    monthIndex = 1;
    dayIndex = 0;
    yearIndex = 2;
  } else {
    monthIndex = 2;
    yearIndex = 0;
    dayIndex = 1;
  }

  return (msg) => {
    const match = msg.match(MSG_PATTERN[system]);
    const dateParts = getDateParts(match[1]);
    const [year, month, day, hour, minute, second] = normalizeParts(
      dateParts, yearIndex, monthIndex, dayIndex, match
    );

    return new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}Z`);
  };
}

/**
 * returns a function that correctly parses a message's date given that a
 * transition of a single day (no month) was found.
 *
 * @param {int[]} oldDate the older date
 * @param {int[]} newDate the newer date
 * @param {int[]} indices an array with a
 */
function makeCase1Function(oldDate, dayIndex, system) {
  const otherIndex1 = (dayIndex + 1) % 3;
  const otherIndex2 = (dayIndex + 2) % 3;
  let yearIndex, monthIndex;

  if (oldDate[otherIndex1] < oldDate[otherIndex2]) {
    monthIndex = otherIndex1;
    yearIndex = otherIndex2;
  } else {
    monthIndex = otherIndex2;
    yearIndex = otherIndex1;
  }

  return (msg) => {
    const match = msg.match(MSG_PATTERN[system]);
    const dateParts = getDateParts(match[1]);
    const [year, month, day, hour, minute, second] = normalizeParts(
      dateParts, yearIndex, monthIndex, dayIndex, match
    );

    return new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}Z`);
  };
}

/**
 * returns a function that correctly parses a message's date given that a
 * transition of month happened.
 */
function makeCase2Function(changes, maxObserved, system) {
  // year is the index that didn't change
  const yearIndex = changes.map((c, i) => [c, i]).filter(([c, i]) => c === 0)[0][1];
  const otherIndex1 = (yearIndex + 1) % 3;
  const otherIndex2 = (yearIndex + 2) % 3;
  let  monthIndex, dayIndex;

  // Day is the index that changed most, month is the other one.
  if (changes[otherIndex1] > changes[otherIndex2]) {
    dayIndex = otherIndex1;
    monthIndex = otherIndex2;
  } else if (changes[otherIndex1] == changes[otherIndex2]) {
    if (maxObserved[otherIndex1] > maxObserved[otherIndex2]) {
      dayIndex = otherIndex1;
      monthIndex = otherIndex2;
    } else {
      dayIndex = otherIndex2;
      monthIndex = otherIndex1;
    }
  } else {
    dayIndex = otherIndex2;
    monthIndex = otherIndex1;
  }
  // day is the index that became 1

  return (msg) => {
    const match = msg.match(MSG_PATTERN[system]);
    const dateParts = getDateParts(match[1]);
    const [year, month, day, hour, minute, second] = normalizeParts(
      dateParts, yearIndex, monthIndex, dayIndex, match
    );

    return new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}Z`);
  };
}

function makeCase3Function(changes, maxObserved, hasDecreased, system) {
  // year index is the one that didn't decrease
  const yearIndex = hasDecreased.map((h, i) => [h, i]).filter(([h, i]) => !h)[0][1];
  const otherIndex1 = (yearIndex + 1) % 3;
  const otherIndex2 = (yearIndex + 2) % 3;
  let dayIndex, monthIndex;

  const changesWithIndex = changes.map((c, i) => [c, i]);

  // sort by number of changes in increasing order
  changesWithIndex.sort((a, b) => a[0] - b[0]);

  // if there's only one index bellow 12 that's the month, otherwise take the
  // index with the most changes is the day.
  if (maxObserved[otherIndex1] <= 12 && maxObserved[otherIndex2] <= 12) {
    if (changes[otherIndex1] > changes[otherIndex2]) {
      dayIndex = otherIndex1;
      monthIndex = otherIndex2;
    } else {
      dayIndex = otherIndex2;
      monthIndex = otherIndex1;
    }
  } else {
    if (maxObserved[otherIndex1] <= 12) {
      monthIndex = otherIndex1;
      dayIndex = otherIndex2;
    } else {
      monthIndex = otherIndex2;
      dayIndex = otherIndex1;
    }
  }

  return (msg) => {
    const match = msg.match(MSG_PATTERN[system]);
    const dateParts = getDateParts(match[1]);
    const [year, month, day, hour, minute, second] = normalizeParts(
      dateParts, yearIndex, monthIndex, dayIndex, match
    );

    return new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}Z`);
  };
}

/**
 * This function analyzes all the dates in `lines` and returns a function that
 * correctly identifies its parts (year, month, day). It works under the
 * assumption that the times in every line are sorted chronologically. The logic
 * is as follows:
 *
 * It analyzes all messages in order and stores how many times the date changed.
 * The core assumption is that the component that changes the most is the day,
 * followed by the month and finally the year. Ordering the amount of changes
 * observed we can tell what is what.
 *
 * @param {string[]} lines of the chat.
 * @param {string} the identified system for this chat.
 * @returns {function} A function that takes a message and returns correctly its
 *                     date object.
 */
function getDateFormat(lines, system) {
  let oldDateParts = [null, null, null];
  const changes = [0, 0, 0];  // stores how many times each part has changed
  let maxObserved = [0, 0, 0];
  const hasDecreased = [false, false, false]

  for (let line of lines) {
    const match = line.match(MSG_PATTERN[system]);

    if (match) {
      // if this line includes a date, get its parts as numbers. E.g. "3/4/25"
      // becomes [3, 4, 25]
      const newDateParts = getDateParts(match[1]);

      if (oldDateParts[0] === null) {
        // this is the first date seen, set it for comparisson
        oldDateParts = newDateParts;
        maxObserved = newDateParts;
      } else {
        // see which parts have changed since the last date observed
        const indices = howManyChanged(oldDateParts, newDateParts);
        for (let i of indices) {
          changes[i] += 1;
        }
        for (let i = 0; i < 3; i++) {
          if (newDateParts[i] > maxObserved[i]) {
            maxObserved[i] = newDateParts[i];
          }
          if (newDateParts[i] < oldDateParts[i]) {
            hasDecreased[i] = true;
          }
        }
        oldDateParts = newDateParts;
      }
    }
  }

  // How many date components changed?
  const numChanges = changes.map((c) => c !== 0).reduce((a, b) => a + b, 0);

  if (numChanges === 0) {
    // nothing changed (only one date was observed in the export)
    return makeCase0Function(oldDateParts, system);
  } else if (numChanges === 1) {
    // only the day ever changed.
    const dayIndex = changes
      .map((c, i) => [c, i])
      .filter(([c, i]) => c > 0)[0][1];
    return makeCase1Function(oldDateParts, dayIndex, system);
  } else if (numChanges === 2) {
    // date and month changed
    return makeCase2Function(changes, maxObserved, system);
  } else {
    // everything changed
    return makeCase3Function(changes, maxObserved, hasDecreased, system);
  }
}

// Parse messages from lines and create an index
export const parseAndIndex = (lines, system) => {
    const getDate = getDateFormat(lines, system);

    const result = [];
    lines.forEach((line) => {

        // Clean unicode from line
        line = line.replaceAll(/[\u200E\u200F\u202A-\u202E\u200B]/g, '');

        const msg = parseMessage(line, system, getDate);

        if (msg && !isInTheIgnoreList(msg.message)) {
            result.push(msg);
        } else {
            // If message is just text without datestring,
            // append it to the previous message.
            if (result[result.length - 1] &&
                // FIXME: check asian date formate
                (system == "ANDROID" && line.substring(2,1) !== "/" &&
                    line.indexOf("a. m.") == -1 &&
                    line.indexOf("p. m.") == -1) ||

                (system == "IOS" &&
                line.indexOf("[") == -1))
            {
                result[result.length - 1].message += " " + line.replaceAll("\r", "");
            }
        }
    })
    return result;
}

/**
 *
 * @param {string} text
 * @returns {object} GeoJSON
 */
function whatsAppParser({ text }) {
    if (!text) return;

    // Split the full text in lines
    const lines = text.split("\n").filter(x => x);

    // Detect system (Android, iOS, ...)
    let system;
    for (let i = 0; i < lines.length; i++) {
        system = detectSystem(lines[i]);
        if (system !== "UNKNOWN") {
            break;
        }
    };

    // Get message objects from text lines
    const messages = parseAndIndex(lines, system);

    return messages;
}

whatsAppParser._name = 'WhatsApp';

export default whatsAppParser;
