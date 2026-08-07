// kwrt-mediahub / luci-app-mediahub ipk 构建:node build-ipk.js [NAME] [VER] [PKGDIR]
// OpenWrt 新版 ipk = gzip(tar):tar 含 ./debian-binary + ./control.tar.gz + ./data.tar.gz
// (旧版是 ar;opkg 现在只认 tar 包装,裸 ar / gzip(ar) 都会判 Malformed)
// 依赖:已生成 <PKGDIR>/control.tar.gz 与 <PKGDIR>/data.tar.gz
const fs=require('fs'),path=require('path'),zlib=require('zlib');
const NAME=process.argv[2]||'kwrt-mediahub';
const VER=process.argv[3]||'1.0.0-1';
const PKGDIR=path.join(__dirname,process.argv[4]||'pkg');

// ustar tar 成员(512 字节头 + 内容 512 对齐)
function tarMember(name,data,mode){
  mode=mode||0o100644;
  const n=(s,l)=>String(s).padEnd(l,'\0');
  const num=(v,l)=>v.toString(8).padStart(l-1,'0')+'\0';
  let header=n(name,100)+num(mode,8)+num(0,8)+num(0,8)+num(data.length,12)+num(0,12)
    +'        '+'0'+n('',100)+'ustar\0'+'00'+n('root',32)+n('root',32)
    +'0000000\0'+'0000000\0'+n('',155)+n('',12);
  // chksum:前 148 字节之和(此时 chksum 为 8 空格)
  let sum=0;for(let i=0;i<512;i++)sum+=header.charCodeAt(i);
  const chk=sum.toString(8).padStart(6,'0')+'\0 ';
  header=header.slice(0,148)+chk+header.slice(156);
  let out=Buffer.from(header);
  out=Buffer.concat([out,data]);
  const pad=(512-(out.length%512))%512;
  if(pad)out=Buffer.concat([out,Buffer.alloc(pad)]);
  return out;
}

const pkg=PKGDIR;
let out=Buffer.concat([
  tarMember('./debian-binary',Buffer.from('2.0\n')),
  tarMember('./control.tar.gz',fs.readFileSync(path.join(pkg,'control.tar.gz'))),
  tarMember('./data.tar.gz',fs.readFileSync(path.join(pkg,'data.tar.gz'))),
  Buffer.alloc(1024), // tar 结束:两个 512 零块
]);
const ipk=`${NAME}_${VER}_all.ipk`;
fs.writeFileSync(path.join(__dirname,ipk),zlib.gzipSync(out)); // 整个包 gzip
console.log('built',ipk,fs.statSync(path.join(__dirname,ipk)).size,'bytes (gzip+tar)');
