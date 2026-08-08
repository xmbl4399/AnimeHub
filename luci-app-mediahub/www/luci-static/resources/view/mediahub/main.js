'use strict';
'require form';
'require view';

function api(action) {
	return fetch('/mediahub-api?action=' + action, { cache: 'no-store' })
		.then(function (r) { return r.json(); })
		.catch(function () { return { ok: false, error: 'API 不可达(检查 nginx/uhttpd)' }; });
}

return view.extend({
	render: function () {
		var m = new form.Map('mediahub', _('AnimeHub'), _('服务主开关、aria2 下载目录全局应用、数据维护与诊断。保存表单后点击下方按钮应用。'));
		var s = m.section(form.TypedSection, 'main', '');
		s.anonymous = true;
		s.addremove = false;

		var o = s.option(form.Value, 'dir', _('aria2 下载目录'), _('默认 /mnt/mmcblk0p7/public/Downloads/Aria2;改这里并应用会同步到 aria2、扫描脚本、nginx 与删除接口'));
		o.rmempty = false;
		o.optional = false;

		o = s.option(form.Value, 'root', _('存储分区目录'), _('媒体存储分区的挂载点(如 /mnt/mmcblk0p7),番剧扫描/网页播放/删除都基于它;一般不用改,换存储盘时才动'));
		o.rmempty = false;
		o.optional = false;

		o = s.option(form.Value, 'fbpass', _('FileBrowser 密码'), _('hub「文件」tab 自动登录用;与 FileBrowser 实际密码保持一致,否则自动登录失败会退回登录页手动输入'));
		o.password = true;
		o.rmempty = false;
		o.optional = false;

		// ---- 操作面板:状态 + 按钮 + 输出(全部用变量引用,避免 DOM 未插入时的 null 访问) ----
		var status = E('div', { 'id': 'mh-status' }, _('加载中...'));
		var out = E('pre', {
			'id': 'mh-out',
			'style': 'white-space:pre-wrap;background:#1c212b;color:#e6edf3;border:1px solid #2a3140;border-radius:6px;padding:10px;min-height:60px;font-size:12px;max-height:300px;overflow:auto'
		}, '');
		var mkBtn = function (text, cls) {
			return E('button', { 'class': 'btn cbi-button ' + (cls || 'cbi-button-action'), 'type': 'button' }, text);
		};
		var bApply = mkBtn(_('立即应用'), 'cbi-button-apply');
		var bDry = mkBtn(_('预览应用(不修改)'), 'cbi-button-neutral');
		var bGetDir = mkBtn(_('读取 aria2 配置'), 'cbi-button-neutral');
		var bRescan = mkBtn(_('立即重扫'), 'cbi-button-neutral');
		var bCache = mkBtn(_('清蜜柑缓存'), 'cbi-button-neutral');
		var bTest = mkBtn(_('连通性测试'), 'cbi-button-neutral');
		var bLog = mkBtn(_('查看 nginx 日志'), 'cbi-button-neutral');
		var bBili = mkBtn(_('清除 B站登录'), 'cbi-button-reset');

		var run = function (action, label) {
			out.textContent = label + ' ...';
			api(action).then(function (j) {
				out.textContent = label + '\n' + JSON.stringify(j, null, 2);
			}).catch(function (e) {
				out.textContent = label + '\n错误: ' + e;
			});
		};
		// 状态栏里的 B站登录状态(独立拉取,清除登录后可刷新)
		var loadBiliStatus = function () {
			api('biliStatus').then(function (j) {
				var el = document.getElementById('mh-bili');
				if (!el) return;
				if (j.isLogin === true) {
					el.innerHTML = '<span style="color:#3ecf8e">● 已登录</span>' + (j.uname ? ' (' + j.uname + ')' : '');
				} else {
					el.innerHTML = '<span style="color:#ff6b6b">● 未登录</span> <span style="color:#888">(mikan 页播放时扫码)</span>';
				}
			}).catch(function () {
				var el = document.getElementById('mh-bili');
				if (el) el.textContent = '查询失败';
			});
		};

		bApply.onclick = function () { run('apply', _('立即应用')); };
		bDry.onclick = function () { run('applydry', _('预览(不修改)')); };
		bRescan.onclick = function () { run('rescan', _('立即重扫 videos.json')); };
		bCache.onclick = function () { run('clearCache', _('清理蜜柑缓存')); };
		bTest.onclick = function () { run('testConn', _('连通性测试')); };
		bLog.onclick = function () { run('logTail', _('nginx 日志尾部')); };
		bBili.onclick = function () {
			out.textContent = _('清除 B站登录 ...');
			api('biliLogout').then(function (j) {
				out.textContent = _('B站登录已清除(下次在蜜柑页播放时重新扫码)') + '\n' + JSON.stringify(j);
				loadBiliStatus();  // 刷新状态栏
			}).catch(function (e) { out.textContent = _('清除失败: ') + e; });
		};
		bGetDir.onclick = function () {
			api('getAria2Dir').then(function (j) {
				out.textContent = _('aria2 当前下载目录: ') + (j.dir || '(未读取到)') +
					'\n' + _('如需修改,请在上方「下载目录」输入框填写后保存并应用');
			});
		};

		var panel = E('div', { 'class': 'cbi-section', 'id': 'mh-panel', 'style': 'margin-top:12px' }, [
			// 服务主开关(OpenClash 风格:点即开/关,无提示)
			E('div', { 'class': 'cbi-section-node', 'style': 'display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;border-bottom:1px solid #2a3140' }, [
				E('div', {}, [
					E('div', { 'style': 'font-weight:600;font-size:14px' }, _('服务主开关')),
					E('div', { 'style': 'color:#888;font-size:12px' }, _('关闭后停用页面反代与定时重扫;点击开关立即生效'))
				]),
				E('button', { 'class': 'btn cbi-button', 'id': 'mh-toggle', 'type': 'button', 'style': 'font-size:14px;font-weight:700;padding:8px 20px;border-radius:6px;min-width:130px;text-align:center' }, '…')
			]),
			E('h3', { 'class': 'cbi-section-title' }, _('状态与操作')),
			status,
			E('div', { 'class': 'cbi-section-node', 'style': 'display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:8px 0' }, [
				bApply, bDry, bGetDir, bRescan, bCache, bTest, bLog, bBili
			]),
			out
		]);

		// 主开关状态与点击切换(即点即生效,不依赖保存/应用)
		var togBtn = null;
		var updateToggle = function (en) {
			if (!togBtn) togBtn = document.getElementById('mh-toggle');
			if (!togBtn) return;
			if (en == 1) {
				togBtn.textContent = '● 运行中(点击关闭)';
				togBtn.style.cssText = 'font-size:14px;font-weight:700;padding:8px 20px;border-radius:6px;min-width:130px;text-align:center;background:#1b5e20;color:#fff;border:1px solid #2e7d32';
			} else {
				togBtn.textContent = '● 已停止(点击开启)';
				togBtn.style.cssText = 'font-size:14px;font-weight:700;padding:8px 20px;border-radius:6px;min-width:130px;text-align:center;background:#b71c1c;color:#fff;border:1px solid #c62828';
			}
		};
		var togglePending = false;
		togBtn = E('button');  // 占位,事件绑定在渲染后
		var bindToggle = function () {
			togBtn = document.getElementById('mh-toggle');
			if (!togBtn || togBtn._bound) return;
			togBtn._bound = true;
			togBtn.onclick = function () {
				if (togglePending) return;
				togglePending = true;
				var cur = (document.getElementById('mh-cur-en') && document.getElementById('mh-cur-en').value === '1') ? 1 : 0;
				api('toggle&enabled=' + (cur ? 0 : 1)).then(function (j) {
					togglePending = false;
					updateToggle(j.enabled);
					// 刷新状态栏
					api('getStatus').then(function (s2) {
						if (s2.ok && document.getElementById('mh-cur-en')) document.getElementById('mh-cur-en').value = s2.enabled;
					});
				}).catch(function () { togglePending = false; });
			};
		};

		return m.render().then(function (html) {
			html.appendChild(panel);
			bindToggle();
			// 状态加载(节点已挂到 html,可直接操作)
			api('getStatus').then(function (j) {
				if (!j.ok) { status.textContent = _('状态获取失败: ') + (j.error || ''); return; }
				var f = function (v) { return v ? '<span style="color:#3ecf8e">● 运行</span>' : '<span style="color:#ff6b6b">● 停止</span>'; };
				status.innerHTML = 'aria2: ' + f(!!j.aria2) + '&nbsp; nginx: ' + f(!!j.nginx) +
					'&nbsp; FileBrowser: <span style="color:' + (j.fb < 500 ? '#3ecf8e' : '#ff6b6b') + '">HTTP ' + j.fb + '</span>' +
					'&nbsp; 网盘: <span style="color:' + (j.pan < 500 ? '#3ecf8e' : '#ff6b6b') + '">HTTP ' + j.pan + '</span>' +
					'&nbsp; B站: <span id="mh-bili">检查中...</span>' +
					'<br>' + _('下载目录') + ': <code>' + j.dir + '</code> | ' + _('媒体根') + ': <code>' + j.root + '</code>';
				updateToggle(j.enabled);
				var hc = document.createElement('input');
				hc.type = 'hidden'; hc.id = 'mh-cur-en'; hc.value = j.enabled;
				html.appendChild(hc);
				loadBiliStatus();
			});
			return html;
		});
	}
});
