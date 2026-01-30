/**
 * It detects the app (WhatsApp, Telegram or Signal)
 * and returns a parser, in a very simple way
 *
 * @param {string} text Full chat text
 * @returns {function} Parser function for the corresponding app
 */

export default async function getAppParser (text) {
    if (!text) return;
    if (text.indexOf('_chatmapId') > -1) { 
        const geoJSONParser = (await import('./geojson')).default
        return geoJSONParser;
    } else if (text[0] === "{") { 
        const module = await import('./telegram');
        return { parser: module.default, searchLocation: module.searchLocation };
    } else if (text.indexOf("group-v2-change") > -1) {
        const module = await import('./signal');
        return { parser: module.default, searchLocation: module.searchLocation };
    }
    const module = await import('./whatsapp');
    return { parser: module.default, searchLocation: module.searchLocation };
}
