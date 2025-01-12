import whatsAppParser from './whatsapp';
import telegramParser from './telegram';

export default function getAppParser (files) {
    for (let filename in files) {
        const text = files[filename];
        if (!text) return;
        if (text[0] === "{") { 
            return telegramParser;
        } else {
            return whatsAppParser;
        }
    }
}
