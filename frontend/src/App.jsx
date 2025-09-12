import React, { useState } from 'react';
import { Camera, Upload, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

// スノーボードトリック分析アプリのメインコンポーネント
const SkateboardTrickAnalyzer = () => {
  // 画像アップロードや分析状態などのステート管理
  const [uploadedImage, setUploadedImage] = useState(null); // アップロード画像のURL
  const [analyzing, setAnalyzing] = useState(false); // 分析中フラグ
  const [analysisResult, setAnalysisResult] = useState(null); // 分析結果
  const [error, setError] = useState(''); // エラーメッセージ
  const [success, setSuccess] = useState(''); // 成功メッセージ

  // 画像アップロード処理（PNGのみ許可）
  const handleImageUpload = async (event) => {
    const file = event.target.files[0]; // ファイル選択イベントから最初のファイルを取得
    if (!file) return; // ファイルが選択されていなければ何もしない

    // 拡張子・MIMEタイプチェック
    const validExt = /\.(png)$/i; // PNG拡張子の正規表現
    if (!validExt.test(file.name) || file.type !== 'image/png') {
      setError('PNG（.png）のみアップロード可能です'); // エラー表示
      setSuccess('');
      return;
    }

    // ここで即時ローカルプレビュー
    setUploadedImage(URL.createObjectURL(file));
    setAnalysisResult(null);
    setSuccess('画像のアップロードに成功しました');
    setError('');
  };

  // 画像分析（Flaskバックエンドの/predict APIを呼び出し）
  const analyzeImage = async () => {
    if (!uploadedImage) return; // 画像がなければ何もしない
    setAnalyzing(true); // 分析中フラグON
    setError("");
    setSuccess("");
    setAnalysisResult(null); // 分析結果をリセット
    try {
      // 画像URLからBlobを取得
      const response = await fetch(uploadedImage);
      const blob = await response.blob();
      const formData = new FormData();
      formData.append("image", blob, "image.png");

      // Flask APIへ画像をPOST
      const res = await fetch("http://localhost:5000/predict", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (res.ok && data.image_url) {
        setUploadedImage(data.image_url); // S3署名付きURLで上書き
      }
      // ↓ ここで受け取ったdata（JSON）を使って画面表示用のstateにセット
      if (data.success) {
        setAnalysisResult({
          successRate: Math.round(data.score * 100),
          confidence: data.confidence ?? 95,
          factors: data.factors || { board: 0, posture: 0 },
          advice: data.advice || "",
          joints: data.joints || null,
        });
        setSuccess("");
        setError("");
      } else {
        setError(data.error || "分析に失敗しました");
        setAnalysisResult(null);
      }
    } catch (err) {
      setError("分析中にエラーが発生しました");
      setAnalysisResult(null);
    } finally {
      setAnalyzing(false);
    }
  };

  // メインアプリケーション画面の描画
  return (
    // 画面全体の背景グラデーション
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* ヘッダー部分（ロゴとタイトルのみ） */}
      <header className="bg-black/20 backdrop-blur-sm border-b border-white/10">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            {/* カメラアイコン */}
            <Camera className="h-8 w-8 text-purple-400" />
            {/* アプリタイトル */}
            <h1 className="text-xl font-bold text-white">SB Analyzer</h1>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* 画像アップロード・分析UIのみ表示 */}
        <div className="max-w-4xl mx-auto space-y-8">
          {/* 画像アップロードセクション */}
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 border border-white/20">
            <h2 className="text-2xl font-bold text-white mb-6 text-center">トリック画像をアップロード</h2>
            {/* 画像未アップロード時のUI */}
            {!uploadedImage ? (
              <div className="border-2 border-dashed border-white/30 rounded-xl p-6 text-center hover:border-purple-400 transition-colors" style={{maxWidth:'340px',margin:'0 auto'}}>
                {/* ファイル選択input（非表示） */}
                <input
                  type="file"
                  id="imageUpload"
                  accept="image/png"
                  onChange={handleImageUpload}
                  className="hidden"
                />
                {/* ラベルをクリックでファイル選択 */}
                <label htmlFor="imageUpload" className="cursor-pointer">
                  {/* アップロードアイコン */}
                  <Upload className="mx-auto h-16 w-16 text-gray-400 mb-4" />
                  <p className="text-white text-lg mb-2">画像をここにドラッグするか、クリックして選択</p>
                  <p className="text-gray-400">PNG（.png）のみ対応</p>
                </label>
              </div>
            ) : (
              <div className="text-center">
                {/* アップロード画像のプレビュー＋関節点プロット */}
                <div style={{ position: 'relative', display: 'inline-block', maxWidth: '416px', maxHeight: '286px' }}>
                  <img
                    src={uploadedImage}
                    alt="Uploaded trick"
                    className="mx-auto rounded-lg shadow-lg mb-4"
                    style={{ maxWidth: '416px', maxHeight: '286px', width: '100%', height: 'auto', display: 'block' }}
                    id="trick-image"
                  />

                </div>
                {/* 成功メッセージ表示 */}
                {success && (
                  <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-3 mt-4">
                    <p className="text-green-200 text-sm">{success}</p>
                  </div>
                )}
                {/* 分析ボタン */}
                <div className="mt-4">
                  <button
                    onClick={analyzeImage}
                    className="bg-purple-500 hover:bg-purple-600 text-white font-bold py-2 px-6 rounded-lg shadow transition-colors duration-150"
                    disabled={analyzing}
                  >
                    {analyzing ? '分析中...' : 'この画像を分析'}
                  </button>
                </div>
                {/* 別画像アップロードボタン */}
                <div className="flex flex-col items-center mt-4">
                  <button
                    onClick={() => {
                      setUploadedImage(null);
                      setAnalysisResult(null);
                    }}
                    className="text-purple-400 hover:text-purple-300 underline"
                  >
                    別の画像をアップロード
                  </button>
                </div>
              </div>
            )}
            {/* エラーメッセージ表示 */}
            {error && (
              <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mt-4">
                <p className="text-red-200 text-sm">{error}</p>
              </div>
            )}
            {error && (
              <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mt-4">
                <p className="text-red-200 text-sm">{error}</p>
              </div>
            )}
          </div>





          {/* 分析中のローディング表示 */}
          {analyzing && (
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 border border-white/20 text-center">
              {/* ローディングスピナー */}
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-400 mx-auto mb-4"></div>
              <h3 className="text-xl font-semibold text-white mb-2">AI分析中...</h3>
              <p className="text-gray-300">画像を解析してトリック成功率を予測しています</p>
            </div>
          )}

          {/* 分析結果の表示 */}
          {analysisResult && (
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 border border-white/20">
              <h3 className="text-2xl font-bold text-white mb-6 text-center">分析結果</h3>
              {/* 成功率・信頼度 */}
              <div className="text-center mb-6">
                <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full ${
                  analysisResult.successRate > 70 ? 'bg-green-500/20 text-green-400' :
                  analysisResult.successRate > 40 ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-red-500/20 text-red-400'
                }`}>
                  {analysisResult.successRate > 70 ? <CheckCircle className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}
                  成功率: {analysisResult.successRate}%
                </div>
                <p className="text-gray-300 mt-2">信頼度: {analysisResult.confidence}%</p>
              </div>
              {/* 改善アドバイス */}
              <div className="bg-white/5 rounded-lg p-4 mb-8">
                <div className="flex items-center gap-2 mb-3">
                  <AlertCircle className="h-5 w-5 text-blue-400" />
                  <h4 className="font-semibold text-white">改善アドバイス</h4>
                </div>
                <div className="w-full min-h-[4em] max-w-full overflow-x-auto">
                  {/* アドバイス文を3行だけ抽出して表示。...も絶対に出さない */}
                  <p className="text-gray-300 whitespace-pre-line break-words">
                    {analysisResult.advice
                      ? analysisResult.advice.split('\n').slice(0, 3).join('\n')
                      : ''}
                  </p>
                </div>
              </div>
              {/* 詳細分析（各要素のスコア） */}
              <div className="space-y-4">
                <h4 className="font-semibold text-white mb-4">詳細分析</h4>
                {/* 目線・体軸・板の反発ごとにスコアを表示 */}
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-300">目線</span>
                    <span className="text-white">{analysisResult.factors.gaze ?? 0}点</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div className={`h-2 rounded-full ${
                      (analysisResult.factors.gaze ?? 0) > 70 ? 'bg-green-500' :
                      (analysisResult.factors.gaze ?? 0) > 40 ? 'bg-yellow-500' : 'bg-red-500'
                    }`} style={{ width: `${analysisResult.factors.gaze ?? 0}%` }}></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-300">体軸（直線）</span>
                    <span className="text-white">{analysisResult.factors.straightness ?? 0}点</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div className={`h-2 rounded-full ${
                      (analysisResult.factors.straightness ?? 0) > 70 ? 'bg-green-500' :
                      (analysisResult.factors.straightness ?? 0) > 40 ? 'bg-yellow-500' : 'bg-red-500'
                    }`} style={{ width: `${analysisResult.factors.straightness ?? 0}%` }}></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-300">体軸（傾き）</span>
                    <span className="text-white">{analysisResult.factors.axis ?? 0}点</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div className={`h-2 rounded-full ${
                      (analysisResult.factors.axis ?? 0) > 70 ? 'bg-green-500' :
                      (analysisResult.factors.axis ?? 0) > 40 ? 'bg-yellow-500' : 'bg-red-500'
                    }`} style={{ width: `${analysisResult.factors.axis ?? 0}%` }}></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-300">体軸（腕）</span>
                    <span className="text-white">{analysisResult.factors.arm ?? 0}点</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div className={`h-2 rounded-full ${
                      (analysisResult.factors.arm ?? 0) > 70 ? 'bg-green-500' :
                      (analysisResult.factors.arm ?? 0) > 40 ? 'bg-yellow-500' : 'bg-red-500'
                    }`} style={{ width: `${analysisResult.factors.arm ?? 0}%` }}></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-300">板の反発</span>
                    <span className="text-white">{analysisResult.factors.rebound ?? 0}点</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div className={`h-2 rounded-full ${
                      (analysisResult.factors.rebound ?? 0) > 70 ? 'bg-green-500' :
                      (analysisResult.factors.rebound ?? 0) > 40 ? 'bg-yellow-500' : 'bg-red-500'
                    }`} style={{ width: `${analysisResult.factors.rebound ?? 0}%` }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};




export default SkateboardTrickAnalyzer;
