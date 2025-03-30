import whatsAppParser from './whatsapp';
import telegramParser from './telegram';
import signalParser from './signal';


/**
 * It detects the app (WhatsApp, Telegram or Signal)
 * and returns a parser, in a very simple way
 *
 * @param {string} text Full chat text
 * @returns {function} Parser function for the corresponding app
 */

export default function getAppParser (text) {
    if (!text) return;
    if (text[0] === "{") { 
        return telegramParser;
    } else if (text.indexOf("group-v2-change") > -1) {
        return signalParser;
    }
    return whatsAppParser;
}
