const x=(e,r)=>{let i=r-1,l=r+1,t,n,d=e[r];for(;(e[i]||e[l])&&!(n&&t);){if(e[i]&&e[i].username===d.username&&!t){const a=Math.abs(e[r].time-e[i].time);t={index:i,delta:a}}if(e[l]&&e[l].username===d.username&&!n){const a=Math.abs(e[r].time-e[l].time);n={index:l,delta:a}}i--,l++}if(t&&n){if(t.delta===n.delta)return{...e[t.index],message:e[t.index].message+". "+e[n.index].message};if(t.delta<n.delta)return e[t.index];if(t.delta>n.delta)return e[n.index]}else{if(t)return e[t.index];if(n)return e[n.index]}return d},o=(e,r)=>u(e,r,1),f=(e,r)=>u(e,r,-1),u=(e,r,i)=>{let l=r+i,t,n=e[r];for(;e[l]&&!t;){if(e[l]&&e[l].username===n.username&&!t){const d=Math.abs(e[r].time-e[l].time);t={index:l,delta:d}}l+=i}return t?e[t.index]:n};export{o as a,f as b,x as g};
//# sourceMappingURL=chatmap--UvUJPGO.js.map
