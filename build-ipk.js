// kwrt-mediahub / luci-app-mediahub ipk 构建:node build-ipk.js [NAME] [VER] [PKGDIR]
// ipk = ar 归档(debian 格式):debian-binary + control.tar.gz + data.tar.gz
// 依赖:已生成 <PKGDIR>/control.tar.gz 与 <PKGDIR>/data.tar.gz
const fs=require('fs'),path=require('path');
const NAME=process.argv[2]||'kwrt-mediahub';
const VER=process.argv[3]||'1.0.0-1';
const PKGDIR=path.join(__dirname,process.argv[4]||'pkg');
function arMember(name,data,mode){
  const pad=(s,n)=>String(s).padEnd(n,' ');
  mode=mode||0o100644;
  const size=data.length;
  const header=pad(name,16)+pad(Math.floor(Date.now()/1000),12)+pad('0',6)+pad('0',6)+pad(mode.toString(8),8)+pad(size,10)+'`\n';
  let out=Buffer.from(header);
  out=Buffer.concat([out,data]);
  if(size%2)out=Buffer.concat([out,Buffer.from('\n')]); // ar 2 字节对齐
  return out;
}
const pkg=PKGDIR;
const out=Buffer.concat([
  Buffer.from('!<arch>\n'),
  arMember('debian-binary',Buffer.from('2.0\n')),
  arMember('control.tar.gz',fs.readFileSync(path.join(pkg,'control.tar.gz'))),
  arMember('data.tar.gz',fs.readFileSync(path.join(pkg,'data.tar.gz'))),
]);
const ipk=`${NAME}_${VER}_all.ipk`;
fs.writeFileSync(path.join(__dirname,ipk),out);
console.log('built',ipk,out.length,'bytes');
