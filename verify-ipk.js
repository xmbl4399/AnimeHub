// verify-ipk.js:检查 kwrt-mediahub ipk 的 ar 结构 + 提取成员供 tar 核对
// 用法:node verify-ipk.js [ipk文件]
const fs=require('fs'),path=require('path');
const ipk=process.argv[2]||path.join(__dirname,'kwrt-mediahub_1.0.0-1_all.ipk');
const b=fs.readFileSync(ipk);
console.log('magic:',JSON.stringify(b.slice(0,8).toString()));
let off=8,ok=true;
while(off<b.length){
  const h=b.slice(off,off+60).toString();
  const name=h.slice(0,16).trim();
  const size=parseInt(h.slice(48,58).trim(),10);
  console.log('member:',name,'size:',size);
  if(h[58]!=='`'||h[59]!=='\n'){ok=false;console.log('BAD HEADER at',off);}
  fs.writeFileSync(path.join(__dirname,'pkg','_'+name),b.slice(off+60,off+60+size));
  off+=60+size+(size%2?1:0);
}
console.log('ar header ok:',ok,'| end:',off,'| file len:',b.length);
