// Pseudo-anonymize usernames

export const hashUsername = async (username) => {
  const encoder = new TextEncoder();
  const data = encoder.encode(username);
  const hash = await window.crypto.subtle.digest("SHA-256", data);
  
  // Convert Uint8Array to hex string
  const hashHex = Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
  
  return hashHex;
};
