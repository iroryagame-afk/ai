(function () {
  "use strict";

  var SOURCES = {
    csn: { label: "美股综合优选", href: "./csn/", tone: "red" },
    rs: { label: "RS 强且加速", href: "./rs-thrust/?view=both", tone: "jade" },
    rotation: { label: "轮动领先加速", href: "./rotation/", tone: "gold" }
  };
  var SAFE_ASSET_CLASSES = new Set(["us_stock", "us_etf_standard"]);
  var TACTICAL_ASSET_CLASSES = new Set(["us_etf_leveraged", "us_etf_inverse", "us_etp_other"]);

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

  function ticker(value) {
    return text(value).replace(/^US\./i, "").trim().toUpperCase();
  }

  function number(value, fallback) {
    var parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function isSafeAsset(row) {
    return SAFE_ASSET_CLASSES.has(row.assetClass || "us_stock");
  }

  function isTacticalAsset(row) {
    return TACTICAL_ASSET_CLASSES.has(row.assetClass || "");
  }

  function put(map, rawTicker, source, row, date, reason) {
    var key = ticker(rawTicker);
    if (!key || !date) return;
    if (!map.has(key)) {
      map.set(key, {
        ticker: key,
        name: row.name || row.memo || row.leader || key,
        industryNote: row.industryNote || row.theme || row.segment || "",
        assetClass: row.assetClass || "us_stock",
        sources: {}
      });
    }
    var item = map.get(key);
    if (item.name === key && (row.name || row.memo || row.leader)) {
      item.name = row.name || row.memo || row.leader;
    }
    if (!item.industryNote && (row.industryNote || row.theme || row.segment)) {
      item.industryNote = row.industryNote || row.theme || row.segment;
    }
    if (row.assetClass) item.assetClass = row.assetClass;
    item.sources[source] = { date: date, reason: reason, row: row };
  }

  function collect(csn, rs, rotation) {
    var map = new Map();
    var csnVerified = csn.status === "VERIFIED" &&
      csn.verifyMarker === "VERIFIED_US_INTEGRATED_RECOMMENDATIONS_ALL_INPUTS_SAME_CLOSE";
    var rsVerified = rs.status === "OPEN_D_VERIFIED";
    var rotationVerified = rotation.status === "OPEN_D_VERIFIED";

    if (csnVerified) {
      (csn.rows || [])
        .filter(function (row) { return isSafeAsset(row); })
        .forEach(function (row) {
          put(
            map,
            row.ticker || row.code,
            "csn",
            row,
            csn.dataDate,
            "综合优选 " + number(row.score, 0).toFixed(1) + "分"
          );
        });
    }

    if (rsVerified) {
      (rs.rows || [])
        .filter(function (row) {
          return (isSafeAsset(row) || isTacticalAsset(row)) &&
            number(row.rsThrustPct, -999) >= 90 &&
            number(row.rsWeekAcceleration, 0) > 0;
        })
        .forEach(function (row) {
          put(
            map,
            row.ticker || row.code,
            "rs",
            row,
            row.dataDate || rs.dataDate,
            "RS Thrust " + number(row.rsThrustPct, 0).toFixed(1) +
              "% · 周加速度 +" + number(row.rsWeekAcceleration, 0).toFixed(1)
          );
        });
    }

    if (rotationVerified) {
      (rotation.rows || [])
        .filter(function (row) {
          return (isSafeAsset(row) || isTacticalAsset(row)) &&
            row.rotationPhase === "领先加速";
        })
        .forEach(function (row) {
          put(
            map,
            row.ticker || row.code,
            "rotation",
            row,
            row.dataDate || rotation.dataDate,
            "领先加速 · 相对速度 " +
              (number(row.relativeVelocity5dPct, 0) >= 0 ? "+" : "") +
              number(row.relativeVelocity5dPct, 0).toFixed(2) + "%"
          );
        });
    }

    return Array.from(map.values()).map(function (item) {
      var dates = Object.values(item.sources).map(function (source) { return source.date; });
      var dateCounts = dates.reduce(function (acc, date) {
        acc[date] = (acc[date] || 0) + 1;
        return acc;
      }, {});
      var commonDate = Object.keys(dateCounts).sort(function (a, b) {
        return dateCounts[b] - dateCounts[a] || b.localeCompare(a);
      })[0];
      item.sources = Object.fromEntries(
        Object.entries(item.sources).filter(function (entry) {
          return entry[1].date === commonDate;
        })
      );
      item.dataDate = commonDate;
      item.toolCount = Object.keys(item.sources).length;
      item.crossModel = Boolean(item.sources.csn && (item.sources.rs || item.sources.rotation));
      item.tactical = isTacticalAsset(item);
      var csnScore = item.sources.csn
        ? number(item.sources.csn.row.score || item.sources.csn.row.model_default_score || item.sources.csn.row.a6_score, 0)
        : 0;
      var rsScore = item.sources.rs
        ? Math.min(100, number(item.sources.rs.row.rsThrustPct, 0))
        : 0;
      var rotationScore = item.sources.rotation
        ? Math.min(100, 50 + number(item.sources.rotation.row.relativeVelocity5dPct, 0) * 8 +
          number(item.sources.rotation.row.relativeAccelerationZ, 0) * 8)
        : 0;
      item.rankScore = csnScore + rsScore + rotationScore;
      return item;
    }).filter(function (item) {
      return item.toolCount === Object.keys(SOURCES).length;
    }).sort(function (a, b) {
      return b.toolCount - a.toolCount ||
        Number(b.crossModel) - Number(a.crossModel) ||
        b.rankScore - a.rankScore ||
        a.ticker.localeCompare(b.ticker);
    });
  }

  function tacticalLabel(item) {
    if (/\bETN\b/i.test(item.name)) return "ETN";
    if (item.assetClass === "us_etf_inverse") return "反向ETF";
    if (item.assetClass === "us_etf_leveraged") return "杠杆ETF";
    return "波动率ETP";
  }

  function card(item, index, tactical) {
    var sourceKeys = Object.keys(item.sources);
    var sourceBadges = sourceKeys.map(function (key) {
      var source = SOURCES[key];
      return '<a class="confluence-tool ' + source.tone + '" href="' + source.href + '">' +
        esc(source.label) + "</a>";
    }).join("");
    var assetLabel = tactical
      ? tacticalLabel(item)
      : (item.assetClass === "us_etf_standard" ? "普通ETF" : "美股个股");
    var modelLabel = item.crossModel ? "跨模型共振" : "同源双模型";
    var extraClass = !tactical && index >= 3 ? " confluence-extra" : "";
    return '<article class="confluence-card' + extraClass + '">' +
      '<div class="confluence-card-head"><div><span class="confluence-kind">' +
      esc(assetLabel) + " · " + esc(modelLabel) + '</span><h3>' +
      esc(item.ticker) + '<small>' + esc(item.name) + "</small></h3></div>" +
      '<strong class="confluence-count">' + item.toolCount + '<small>工具命中</small></strong></div>' +
      '<div class="confluence-tools">' + sourceBadges + "</div></article>";
  }

  function render(items) {
    var section = document.getElementById("strongRecommendations");
    var list = document.getElementById("confluenceList");
    var count = document.getElementById("confluenceCount");
    var status = document.getElementById("confluenceStatus");
    var tacticalSection = document.getElementById("tacticalRecommendations");
    var tacticalList = document.getElementById("tacticalList");
    var tacticalCount = document.getElementById("tacticalCount");
    if (!section || !list || !count || !status ||
        !tacticalSection || !tacticalList || !tacticalCount) return;

    var standardItems = items.filter(function (item) { return !item.tactical; });
    var tacticalItems = items.filter(function (item) { return item.tactical; });
    if (!items.length) {
      section.hidden = true;
      list.innerHTML = "";
      tacticalSection.hidden = true;
      tacticalList.innerHTML = "";
      return;
    }
    section.hidden = false;
    count.textContent = standardItems.length;
    if (!standardItems.length) {
      status.textContent = "本期三工具共振仅出现在高风险战术产品中。";
      list.innerHTML = "";
    } else {
      status.textContent = "仅展示三个工具同日共同命中；研究优先级不等于买点。";
      list.innerHTML = standardItems.map(function (item, index) {
        return card(item, index, false);
      }).join("");
    }

    var button = document.getElementById("confluenceToggle");
    if (standardItems.length <= 3) {
      button.hidden = true;
    } else {
      button.hidden = false;
      button.textContent = "展开其余 " + (standardItems.length - 3) + " 个";
      button.addEventListener("click", function () {
        var expanded = section.classList.toggle("expanded");
        button.textContent = expanded
          ? "收起"
          : "展开其余 " + (standardItems.length - 3) + " 个";
      });
    }

    if (tacticalItems.length) {
      tacticalSection.hidden = false;
      tacticalCount.textContent = tacticalItems.length;
      tacticalList.innerHTML = tacticalItems.map(function (item, index) {
        return card(item, index, true);
      }).join("");
    } else {
      tacticalSection.hidden = true;
      tacticalList.innerHTML = "";
    }
  }

  function fail(message) {
    var section = document.getElementById("strongRecommendations");
    if (section) section.hidden = true;
    console.warn("三工具共振区暂停：" + message);
  }

  Promise.all([
    fetch("./csn/data.json", { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error("CSN HTTP " + response.status);
      return response.json();
    }),
    fetch("./rs-thrust/data.json", { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error("RS HTTP " + response.status);
      return response.json();
    }),
    fetch("./rotation/data.json", { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error("Rotation HTTP " + response.status);
      return response.json();
    })
  ]).then(function (payloads) {
    render(collect(payloads[0], payloads[1], payloads[2]));
  }).catch(function (error) {
    fail(error && error.message ? error.message : "未知错误");
  });
})();
