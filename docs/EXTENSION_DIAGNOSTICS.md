# EXT-001 — 値を出さないmanifestレビューと公式診断照合

2026-11-08 JST。構造検査/ライセンス構文/所有者承認/公式検証を別の証拠として扱う。
正式Extensionの生成・インストール・公開や、部品のライセンス選択は行わない。

## 非実行のTOMLレビュー

```text
python -m cbdk extension-manifest-review <manifest.toml> --output reports/latest/manifest_review.json
```

32KiBまでの通常TOMLをデータとして読むだけで、隣のPythonやaddonを実行しない。
既存の必須項目検査を再利用し、項目別のmissing/invalid/valid_in_supported_subsetと
固定の修正案内を出力する。入力値、maintainer情報、元ファイルのパスを含めず、
未対応キー名もgenericなunsupported_fieldへ置換する。構文不正のメッセージも固定文のみ。

出力は新規のignored reports/latest/*.jsonだけ。既存ファイル・脱出・出力先symlink脱出を拒否。
入力symlink/重複キー/超過サイズも拒否し、原本は変更しない。
JSONのstatusはreview_onlyで、official_validation_ran/release_authorizedはfalse。
構造が妥当でもSPDXの存在・互換性・権利・所有者承認の証明ではない。

同じ項目別案内をextension-preflightのmanifest_field_diagnosticsにも追加した。
既存のrelease-blocked判定とレガシーZIP生成は維持する。

## 公式CLI結果との照合

observe_official_validation / compare_official_validationは、上限付きの実行結果を
accepted/rejected/unclassifiedへ正規化し、既知項目のmissing/invalidだけを保持する。
生ログやパス/値は保存しない。ログの真正性を認証するAPIではない。

終了0だけでは成功としない。既知の成功マーカーも必要。拒否は正の終了コードと既知の
項目診断を要し、signal終了/原因不明/成功とエラーが矛盾する結果はunclassified。
想定と異なる項目はdisagreement、診断の一部だけ一致する場合はpartial_diagnostic_agreement。
対応外項目はoutside_supported_subsetであり、どれも完全一致と数えない。
文言が変わった公式版も黙って成功へ昇格せず、実測を読んで対応する。

CIはコードを含まない合成manifestの正常/ライセンス欠落/tagline/id/version/maintainer不正の
6例を生成し、実際の公式Blender extension validateの終了コードと項目診断を照合する。
__init__.pyはimport時に例外になるダミーで、validatorがaddonをロードしないことも維持。
SPDX例は合成データの値で、CBDKや部品へのライセンス決定ではない。

## 実装時点の検証

ローカルPython839件成功。Blender4.3.2で6合成例の完全診断一致を確認。
対象3版/Windowsの今回CIは未実行。最新結果はSTATE/本書の追補を参照。
実Windows GUI/実ユーザー/ライセンス・承認/実Extension全体は未確認のまま。
