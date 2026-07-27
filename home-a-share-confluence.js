(function () {
  "use strict";

  function text(value) {
    return String(value == null ? "" : value);
  }

  function esc(value) {
    return text(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function card(row) {
    return '<article class="confluence-card">' +
      '<div class="confluence-card-head"><div>' +
      '<span class="confluence-kind">A股 · ' + esc(row.pool) + ' · 研究优先</span>' +
      '<h3>' + esc(row.ticker) + '<small>' + esc(row.name) + '</small></h3>' +
      '</div><strong class="confluence-count">2<small>模型命中</small></strong></div>' +
      '<div class="confluence-tools">' +
      '<a class="confluence-tool red" href="./mda100/">A股严选 · 建议买入</a>' +
      '<span class="confluence-tool jade">30分钟缠论 · ' + esc(row.chanlun_action) + '</span>' +
      '</div>' +
      '<p style="margin:8px 0 0;color:var(--ink-2);font-size:10.5px;line-height:1.5">' +
      esc(row.theme) + '<br>' +
      '买入观察区 ' + esc(row.buy_zone) + '；防守参考 ' + esc(row.defense) + '。<br>' +
      '缠论条件：' + esc(row.chanlun_signal) + '。</p>' +
      '</article>';
  }

  function fail(message) {
    var section = document.getElementById("aShareConfluence");
    if (section) section.hidden = true;
    console.warn("A股双模型交集暂停：" + message);
  }

  fetch("./a-share-confluence/data.json", { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(function (payload) {
      var section = document.getElementById("aShareConfluence");
      var list = document.getElementById("aShareConfluenceList");
      var count = document.getElementById("aShareConfluenceCount");
      var status = document.getElementById("aShareConfluenceStatus");
      if (!section || !list || !count || !status) return;
      if (payload.status !== "DOUBLE_VERIFIED_A_SHARE_CONFLUENCE" ||
          payload.source_dates_match !== true) {
        throw new Error("核验标记或日期一致性不通过");
      }
      var rows = Array.isArray(payload.rows) ? payload.rows : [];
      if (!rows.length) {
        section.hidden = true;
        return;
      }
      section.hidden = false;
      count.textContent = rows.length;
      status.textContent =
        payload.data_date + " 同日交集；A股严选给出建议买入，缠论仅给买入观察/确认条件，不代表下单。";
      list.innerHTML = rows.map(card).join("");
    })
    .catch(function (error) {
      fail(error && error.message ? error.message : "未知错误");
    });
})();
