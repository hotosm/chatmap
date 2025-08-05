/**
 * It detects the app (WhatsApp, Telegram or Signal)
 * and returns a parser, in a very simple way
 *
 * @param {string} text Full chat text
 * @returns {function} Parser function for the corresponding app
 */

export default async function getAppParser (text) {
    if (!text) return;
    if (text[0] === "{") { 
        const telegramParser = (await import('./telegram')).default
        return telegramParser;
    } else if (text.indexOf("group-v2-change") > -1) {
        const signalParser = (await import('./signal')).default
        return signalParser;
    }
    const whatsappParser = (await import('./whatsapp')).default
    return whatsappParser;
}
