// verify-ipk.js:检查 ipk 结构(gzip+tar 包装)+ 提取成员供 tar 核对
// 用法:node verify-ipk.js [ipk文件]
const fs=require('fs'),path=require('path'),zlib=require('zlib');
const ipk=process.argv[2]||path.join(__dirname,'kwrt-mediahub_1.0.0-1_all.ipk');
const raw=fs.readFileSync(ipk);
const b=(raw[0]===0x1f&&raw[1]===0x8b)?zlib.gunzipSync(raw):raw;
console.log('ipk 大小:',raw.length,'| 解压后:',b.length,'| tar magic:',JSON.stringify(b.slice(257,263).toString()));
// 遍历 tar 成员
let off=0,ok=true;
while(off+512<=b.length){
  const block=b.slice(off,off+512);
  if(block.every(x=>x===0))break; // 结束块
  const name=block.slice(0,100).toString().replace(/\0.*$/,'');
  const size=parseInt(block.slice(124,136).toString().replace(/\0.*$/,'').trim(),8)||0;
  if(!name){ok=false;break;}
  console.log('member:',name,'size:',size);
  fs.writeFileSync(path.join(__dirname,'pkg','_'+name.replace(/^\.\//,'')),b.slice(off+512,off+512+size));
  off+=512+Math.ceil(size/512)*512;
}
console.log('tar 解析 ok:',ok,'| end:',off,'| len:',b.length);
