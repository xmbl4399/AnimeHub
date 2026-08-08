/* 播放器公共逻辑(anime/mikan 共用):弹幕按钮组迁移 + 全屏横屏锁 + B站弹幕解析 */
(function(){
  // 弹幕按钮组(插件开关/设置/样式)移入控制条时长条右侧(.art-controls-center),
  // MutationObserver 持续运行:ArtPlayer 重建控制条(全屏进出)时自动归位
  window.setupDmButtonGroup=function(containerId){
    const box=document.getElementById(containerId);
    if(!box)return;
    const moveDm=()=>{
      try{
        const dm=box.querySelector('.artplayer-plugin-danmuku');
        const center=box.querySelector('.art-controls-center');
        if(dm&&center&&dm.parentElement!==center){
          center.insertBefore(dm,center.firstChild);
          dm.style.cssText='';
          return true;
        }
      }catch(e){}
      return false;
    };
    try{
      const obs=new MutationObserver(()=>{moveDm();});
      obs.observe(box,{childList:true,subtree:true});
    }catch(e){}
    moveDm();
  };
  // 全屏时尝试锁定横屏(Android Chromium 生效;iOS 视频全屏天然横屏,lock 不支持则静默)
  window.bindFullscreenRotate=function(a){
    if(!a)return;
    a.on('fullscreen',st=>{
      try{
        if(st&&screen.orientation&&screen.orientation.lock){
          setTimeout(()=>{screen.orientation.lock('landscape').catch(()=>{});},250);
        }else if(!st&&screen.orientation&&screen.orientation.unlock){
          screen.orientation.unlock();
        }
      }catch(e){}
    });
  };
  // B站弹幕 XML → ArtPlayer 插件数组
  window.parseBiliDm=function(xml){
    if(!xml||xml.indexOf('<d')<0)return [];
    try{
      const doc=new DOMParser().parseFromString(xml,'text/xml');
      const ds=doc.querySelectorAll('d[p]');
      const list=[];
      ds.forEach(d=>{
        const p=d.getAttribute('p').split(',');
        const m=+p[1]||1;const col=+p[3]||16777215;
        list.push({text:d.textContent,mode:(m==4?2:m==5?1:0),color:'#'+col.toString(16).padStart(6,'0'),time:+p[0]||0});
      });
      return list;
    }catch(e){return [];}
  };
})();
