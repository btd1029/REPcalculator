/**
 * PIA質問票 v1.8 — Gem出力(JSON)自動転記ツール
 * ------------------------------------------------------------------
 * 使い方（人の操作は3ステップ）
 *   1. Gem「PIAアシスタント」の出力から <PIA_JSON>...</PIA_JSON> ブロックをコピー
 *   2. マスターテンプレを開き、メニュー「PIA転記 > JSONを貼って転記」
 *   3. ダイアログにJSONを貼って「転記」→ 専用フォルダに新規PIAが生成される
 *
 * 初回のみ：メニュー「PIA転記 > セットアップ（名前付き範囲を作成）」を1回実行。
 * ------------------------------------------------------------------
 * ※ CONFIG は必ずあなたのテンプレに合わせて調整してください（下記コメント参照）。
 */

// ============================================================
// CONFIG — ここだけ自分の環境に合わせて編集する
// ============================================================
const CONFIG = {
  // 生成したPIAコピーを入れる専用フォルダのID
  // （ドライブでフォルダを開いたときURLの .../folders/★ここ★ ）
  destFolderId: 'PUT_YOUR_FOLDER_ID_HERE',

  // 質問票テンプレ内のシート名（実ファイルに合わせる）
  sheets: {
    initial: '初期アセスメント',   // Section 1〜2
    dpiaCheck: 'DPIA要否判定',     // Section 3
    summary: 'Summary',            // Section 4
    risk: 'リスクアセスメント',    // Section 5
    action: 'アクションアイテム',  // Section 6
    signoff: '承認',               // Section 7
  },

  // スカラー項目：項番ラベルを探す列(labelCol)と、回答を書く列(answerCol)。
  // グループ単位で定義（テンプレの表ごとに回答列が違うため）。列は1始まり(A=1)。
  // setup() がこの定義で labelCol から項番を探し、同じ行の answerCol に
  // 名前付き範囲 q_<項番> を作成する（以後は行がずれても自動追従）。
  scalarGroups: [
    { sheet: 'initial',   labelCol: 1, answerCol: 3,
      keys: ['1.1','1.2.1','1.2.2','1.2.3','1.3',
             '2.1','2.2','2.3','2.4','2.5','2.6',
             '3.1','4.1','5.1','6.1',
             '7.1','7.2','7.3',
             '8.1','8.2','8.3','8.4'] },
  ],

  // 繰り返し表：先頭データ行のアンカー（列は書き込む最左列）。
  // setup() がこのセルに名前付き範囲を作る。transcribe() が必要行数だけ
  // 下に行挿入（書式・数式コピー）して配列を流し込む。
  repeaters: {
    dpiaCriteria: { sheet: 'dpiaCheck', anchorCell: 'D4',
      cols: { applies: 0, comment: 1 } },              // 該否, コメント（アンカー基準の相対列）
    risks: { sheet: 'risk', anchorCell: 'C4',
      cols: { risk: 0, p: 1, i: 2, mitigation: 3, m: 4 } }, // 残存(列F)はテンプレ数式に任せる
    actions: { sheet: 'action', anchorCell: 'B4',
      cols: { item: 0, rank: 1, owner: 2, status: 3, due: 4 } },
  },

  // DPIA不要時に理由を書くセル（Summary末尾「DPIAを実施しない理由」）
  dpiaNoneReasonCell: { sheet: 'summary', cell: 'B60' },

  // 残存リスクの数式がある列（検算用。C4アンカーに対し残存はF列＝相対+3）
  riskResidualColOffset: 3,
};

// DPIA判定9基準（Section 3）の固定順。criteria[i].no と対応。
const DPIA_CRITERIA_COUNT = 9;

// ============================================================
// メニュー
// ============================================================
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('PIA転記')
    .addItem('JSONを貼って転記', 'showTranscribeDialog')
    .addSeparator()
    .addItem('セットアップ（名前付き範囲を作成）', 'setupNamedRanges')
    .addToUi();
}

function showTranscribeDialog() {
  const html = HtmlService.createHtmlOutputFromFile('Dialog')
    .setWidth(520).setHeight(460);
  SpreadsheetApp.getUi().showModalDialog(html, 'PIA JSON を貼り付け');
}

// ============================================================
// セットアップ：項番ラベルを探して名前付き範囲を作成
// ============================================================
function setupNamedRanges() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const created = [];
  const missing = [];

  // スカラー項目
  CONFIG.scalarGroups.forEach(group => {
    const sh = ss.getSheetByName(CONFIG.sheets[group.sheet]);
    if (!sh) { missing.push('シート未検出: ' + group.sheet); return; }
    const labelValues = sh.getRange(1, group.labelCol, sh.getLastRow(), 1).getValues();
    group.keys.forEach(key => {
      let row = -1;
      for (let r = 0; r < labelValues.length; r++) {
        if (String(labelValues[r][0]).trim() === key) { row = r + 1; break; }
      }
      if (row === -1) { missing.push('項番 ' + key + ' が ' + group.sheet + ' に見つからない'); return; }
      const rng = sh.getRange(row, group.answerCol);
      ss.setNamedRange('q_' + key.replace(/\./g, '_'), rng);
      created.push('q_' + key.replace(/\./g, '_'));
    });
  });

  // 繰り返し表アンカー
  Object.keys(CONFIG.repeaters).forEach(name => {
    const rep = CONFIG.repeaters[name];
    const sh = ss.getSheetByName(CONFIG.sheets[rep.sheet]);
    if (!sh) { missing.push('シート未検出: ' + rep.sheet); return; }
    ss.setNamedRange(name + '_start', sh.getRange(rep.anchorCell));
    created.push(name + '_start');
  });

  // DPIA不要理由セル
  const sumSh = ss.getSheetByName(CONFIG.sheets[CONFIG.dpiaNoneReasonCell.sheet]);
  if (sumSh) {
    ss.setNamedRange('dpia_none_reason', sumSh.getRange(CONFIG.dpiaNoneReasonCell.cell));
    created.push('dpia_none_reason');
  }

  SpreadsheetApp.getUi().alert(
    'セットアップ完了',
    '作成: ' + created.length + '件\n' +
    (missing.length ? '⚠ 未処理:\n- ' + missing.join('\n- ') : '未処理なし'),
    SpreadsheetApp.getUi().ButtonSet.OK);
}

// ============================================================
// 転記本体（ダイアログから呼ばれる）
// 戻り値：{ok, messages[], url} をダイアログJSに返す
// ============================================================
function transcribe(jsonText) {
  // 1) パース（ハードエラー）
  let data;
  try {
    data = JSON.parse(jsonText);
  } catch (e) {
    return { ok: false, hard: true, messages: ['JSONのパースに失敗: ' + e.message + '（コピペ崩れの可能性）'] };
  }

  // 2) 検証（ハード／ソフト）
  const v = validate(data);
  if (v.hard.length) {
    return { ok: false, hard: true, messages: v.hard };
  }

  // 3) マスター複製 → 命名 → フォルダ配置
  const master = SpreadsheetApp.getActiveSpreadsheet();
  const name = buildFileName(data);
  const folder = DriveApp.getFolderById(CONFIG.destFolderId);
  const copyFile = DriveApp.getFileById(master.getId()).makeCopy(name, folder);
  const copy = SpreadsheetApp.openById(copyFile.getId());

  // 4) 書き込み
  writeScalars(copy, data);
  writeRepeater(copy, 'dpiaCriteria', normalizeDpiaCriteria(data.dpia_criteria));
  if (data.meta.dpia_required) {
    writeRepeater(copy, 'risks', data.risks || []);
    writeRepeater(copy, 'actions', data.actions || []);
  } else {
    // 2段階運用：DPIA不要ならSection4末尾に理由を書き、Section4〜7は空のまま
    const r = copy.getRangeByName('dpia_none_reason');
    if (r) r.setValue(data.meta.dpia_reason || 'DPIA不要（理由未記入）');
  }

  // 5) 残存リスクの検算（ソフト警告に追加）
  const residualWarnings = crossCheckResiduals(copy, data);
  const allWarnings = v.soft.concat(residualWarnings);

  // 6) 転記ログを1タブ残す
  writeLog(copy, jsonText, allWarnings);

  return {
    ok: true, hard: false,
    messages: allWarnings.length ? ['転記完了（警告あり）:'].concat(allWarnings) : ['転記完了。警告なし。'],
    url: copy.getUrl(),
    name: name,
  };
}

// ============================================================
// 検証
// ============================================================
function validate(data) {
  const hard = [], soft = [];

  // 必須
  if (!data.meta) hard.push('meta がありません');
  else {
    if (!data.meta.project_name) soft.push('meta.project_name 未設定（暫定名で保存されます）');
    if (!data.meta.jurisdiction || !data.meta.jurisdiction.length) hard.push('meta.jurisdiction が未設定');
    if (typeof data.meta.dpia_required !== 'boolean') hard.push('meta.dpia_required が真偽値でない');
  }

  // 未知の項番キー（ソフト）
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (data.fields) {
    Object.keys(data.fields).forEach(k => {
      if (!ss.getRangeByName('q_' + k.replace(/\./g, '_'))) {
        soft.push('未知の項番キー（テンプレに対応セルなし・スキップ）: ' + k);
      }
    });
  }

  // 段階矛盾（ソフト）
  if (data.meta && data.meta.dpia_required === false) {
    if ((data.risks && data.risks.length) || (data.actions && data.actions.length)) {
      soft.push('dpia_required=false なのに risks/actions が入っています（Section4〜7はスキップされます）');
    }
    (data.risks || []).forEach((r, i) => {
      const res = num(r.p) + num(r.i) - num(r.m);
      if (res >= 4) soft.push('dpia_required=false だが risks[' + i + '] の残存が ' + res + '（4以上）');
    });
  }

  return { hard, soft };
}

// ============================================================
// 書き込みヘルパ
// ============================================================
function writeScalars(copy, data) {
  if (!data.fields) return;
  Object.keys(data.fields).forEach(k => {
    const rng = copy.getRangeByName('q_' + k.replace(/\./g, '_'));
    if (!rng) return; // 未知キーは検証で警告済み
    const val = data.fields[k];
    rng.setValue(val === 'TBD' || val === null || val === '' ? 'TBD（要記入）' : val);
  });
}

function writeRepeater(copy, name, rows) {
  const rep = CONFIG.repeaters[name];
  const anchor = copy.getRangeByName(name + '_start');
  if (!anchor || !rows || !rows.length) return;
  const sh = anchor.getSheet();
  const startRow = anchor.getRow();
  const startCol = anchor.getColumn();

  // 必要行数だけ、先頭データ行を下に挿入コピー（書式・数式維持）
  if (rows.length > 1) {
    sh.insertRowsAfter(startRow, rows.length - 1);
    sh.getRange(startRow, 1, 1, sh.getLastColumn())
      .copyTo(sh.getRange(startRow + 1, 1, rows.length - 1, sh.getLastColumn()));
  }

  // 値を配置
  rows.forEach((row, i) => {
    const r = startRow + i;
    Object.keys(rep.cols).forEach(field => {
      const c = startCol + rep.cols[field];
      let val = row[field];
      if (val === 'TBD' || val === null || val === undefined || val === '') val = 'TBD';
      // applies(該否)は true/false → 「該当/非該当」
      if (name === 'dpiaCriteria' && field === 'applies') val = row.applies ? '該当' : '非該当';
      sh.getRange(r, c).setValue(val);
    });
  });
}

// DPIA9基準を no 昇順・9件そろえる（欠けは非該当扱い）
function normalizeDpiaCriteria(criteria) {
  const map = {};
  (criteria || []).forEach(c => { map[c.no] = c; });
  const out = [];
  for (let n = 1; n <= DPIA_CRITERIA_COUNT; n++) {
    out.push(map[n] || { no: n, applies: false, comment: '' });
  }
  return out;
}

// 残存リスクの検算：テンプレ数式の結果 vs Gemの residual
function crossCheckResiduals(copy, data) {
  const warnings = [];
  if (!data.meta.dpia_required || !data.risks) return warnings;
  const anchor = copy.getRangeByName('risks_start');
  if (!anchor) return warnings;
  const sh = anchor.getSheet();
  const startRow = anchor.getRow();
  const resCol = anchor.getColumn() + CONFIG.riskResidualColOffset;
  SpreadsheetApp.flush();
  data.risks.forEach((r, i) => {
    if (r.residual === undefined) return;
    const sheetVal = sh.getRange(startRow + i, resCol).getValue();
    if (Number(sheetVal) !== Number(r.residual)) {
      warnings.push('risks[' + i + '] 残存の不一致: Gem=' + r.residual + ' / テンプレ計算=' + sheetVal);
    }
  });
  return warnings;
}

// ============================================================
// 命名・ログ
// ============================================================
function buildFileName(data) {
  const proj = (data.meta && data.meta.project_name) ? data.meta.project_name : null;
  const date = (data.meta && data.meta.date) ? data.meta.date : todayStr_();
  let base = proj ? ('PIA_' + proj + '_' + date)
                  : ('PIA_未設定_' + date + '_' + Utilities.formatDate(new Date(), 'JST', 'HHmmss'));
  // 衝突回避 _v2, _v3...
  const folder = DriveApp.getFolderById(CONFIG.destFolderId);
  let name = base, n = 1;
  while (folder.getFilesByName(name).hasNext()) { n++; name = base + '_v' + n; }
  return name;
}

function writeLog(copy, jsonText, warnings) {
  const sh = copy.insertSheet('_転記ログ');
  const hash = Utilities.base64Encode(
    Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, jsonText)).slice(0, 16);
  const rows = [
    ['転記日時', new Date()],
    ['元JSONハッシュ(先頭16)', hash],
    ['警告件数', warnings.length],
  ].concat(warnings.map((w, i) => ['警告' + (i + 1), w]));
  sh.getRange(1, 1, rows.length, 2).setValues(rows);
  sh.setColumnWidth(2, 600);
}

function todayStr_() { return Utilities.formatDate(new Date(), 'JST', 'yyyy-MM-dd'); }
function num(x) { return Number(x) || 0; }
