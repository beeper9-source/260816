// pyodide_worker.js - Pyodide runner in a background Web Worker

// Import Pyodide from CDN
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js");

let pyodide = null;

// Send logs to main thread
function sendLog(message, level = "python") {
    postMessage({
        type: "log",
        data: { message, level }
    });
}

// Send progress updates to main thread
function sendProgress(text, percent) {
    postMessage({
        type: "progress",
        data: { text, percent }
    });
}

// Initialize Pyodide and install libraries
async function initPyodide() {
    try {
        sendProgress("Pyodide 로딩 중...", 15);
        
        // Load Pyodide and redirect Python prints (stdout/stderr) to JS logs
        pyodide = await loadPyodide({
            stdout: (text) => sendLog(text, "python"),
            stderr: (text) => sendLog(text, "error")
        });

        sendProgress("micropip 패키지 로딩 중...", 35);
        await pyodide.loadPackage("micropip");

        sendProgress("music21 패키지 설치 중 (최초 1회, 15~20초 소요)...", 60);
        const micropip = pyodide.pyimport("micropip");
        await micropip.install("music21");

        sendProgress("기타 HMM 모델 파일 로딩 중...", 85);
        
        // Fetch and write local python scripts to Pyodide's virtual filesystem
        const resHmm = await fetch("guitar_hmm.py");
        const codeHmm = await resHmm.text();
        pyodide.FS.writeFile("guitar_hmm.py", codeHmm);

        const resParser = await fetch("mxl_parser.py");
        const codeParser = await resParser.text();
        pyodide.FS.writeFile("mxl_parser.py", codeParser);

        sendProgress("시스템 로드 성공!", 100);
        postMessage({ type: "ready" });
        
    } catch (err) {
        postMessage({
            type: "error",
            data: { message: err.message }
        });
    }
}

// Start loading immediately
initPyodide();

// Listen for files to process
onmessage = async (event) => {
    const { type, data } = event.data;

    if (type === "process") {
        try {
            const { arrayBuffer, fileName } = data;
            sendLog(`파일 분석 시작: ${fileName}`);

            // Write input file to Pyodide filesystem
            const fileBytes = new Uint8Array(arrayBuffer);
            pyodide.FS.writeFile("input.mxl", fileBytes);

            // Execute Python solver via Pyodide
            sendLog("HMM Viterbi 계산 실행 중...");
            
            const pythonScript = `
import mxl_parser
annotated_count, total_count = mxl_parser.annotate_mxl("input.mxl", "output.mxl")
`;
            await pyodide.runPythonAsync(pythonScript);

            // Read result from Pyodide filesystem
            const resultBytes = pyodide.FS.readFile("output.mxl");
            
            // Extract statistics from python
            const annotatedCount = pyodide.globals.get("annotated_count");
            const totalCount = pyodide.globals.get("total_count");

            // Clean up files in Pyodide FS
            pyodide.FS.unlink("input.mxl");
            pyodide.FS.unlink("output.mxl");

            // Send arrayBuffer and stats back to main thread
            postMessage({
                type: "result",
                data: {
                    arrayBuffer: resultBytes.buffer,
                    annotatedCount: annotatedCount,
                    totalCount: totalCount
                }
            }, [resultBytes.buffer]); // Transfer buffer to avoid copying

        } catch (err) {
            postMessage({
                type: "error",
                data: { message: err.message }
            });
        }
    }
};
