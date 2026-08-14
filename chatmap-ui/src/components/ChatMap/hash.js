// Pseudo-anonymize usernames

const hashUsername = async (username) => {
  const encoder = new TextEncoder();
  const data = encoder.encode(username);
  const hash = await window.crypto.subtle.digest("SHA-256", data);
  
  // Convert Uint8Array to hex string
  const hashHex = Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
  
  return hashHex;
};

export const hashUsernames = async (usernames) => {
  const res = await Promise.all(
    Object.keys(usernames).map(async u => { return {[u]: await hashUsername(u)} } )
  );
  const dict = {};
  for (let i = 0; i < res.length; i++) {
    let k = Object.keys(res[i])[0];
    dict[k] = res[i][k];
  }
  return dict;
}