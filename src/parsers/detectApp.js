import whatsAppParser from './whatsapp';
import telegramParser from './telegram';
import signalParser from './signal';

export default function getAppParser (files) {
    for (let filename in files) {
        const text = files[filename];
        if (!text) return;
        if (text[0] === "{") { 
            return telegramParser;
        } else if (text.indexOf("group-v2-change") > -1) {
            return signalParser;
        }
        return whatsAppParser;
    }
}
