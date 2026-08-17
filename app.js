// App.js - Coordinates UI and Worker Communication

let worker = null;
let currentFileName = "";

// UI Container Elements
const loadingContainer = document.getElementById("loading-container");
const uploadContainer = document.getElementById("upload-container");
const processingContainer = document.getElementById("processing-container");
const completeContainer = document.getElementById("complete-container");

const loadingStatus = document.getElementById("loading-status");
const initProgress = document.getElementById("init-progress");
const logConsole = document.getElementById("log-console");

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");

const downloadLink = document.getElementById("download-link");
const resultSummary = document.getElementById("result-summary");

// Initialize application
document.addEventListener("DOMContentLoaded", () => {
    initWorker();
    setupDragAndDrop();
});

// Create and initialize Pyodide Web Worker
function initWorker() {
    log("System", "Web Worker 인스턴스 생성 중...");
    worker = new Worker("pyodide_worker.js?v=" + new Date().getTime());

    worker.onmessage = (event) => {
        const { type, data } = event.data;

        switch (type) {
            case "log":
                log("Python", data.message, data.level);
                break;

            case "progress":
                updateProgress(data.text, data.percent);
                break;

            case "ready":
                log("System", "Python 및 music21 엔진 준비 완료!", "success-log");
                showState("upload");
                break;

            case "result":
                handleResult(data.arrayBuffer, data.annotatedCount, data.totalCount);
                break;

            case "error":
                log("System", `치명적 오류 발생: ${data.message}`, "error");
                showState("upload");
                alert(`오류가 발생했습니다:\n${data.message}`);
                break;
        }
    };
}

// Append log messages to console
function log(sender, message, level = "system") {
    const line = document.createElement("div");
    line.className = `log-line ${level}`;
    line.textContent = `[${sender}] ${message}`;
    logConsole.appendChild(line);
    
    // Auto scroll to bottom
    logConsole.scrollTop = logConsole.scrollHeight;
}

// Update loading progress bar
function updateProgress(text, percent) {
    loadingStatus.textContent = text;
    initProgress.style.width = `${percent}%`;
    log("System", `${text} (${percent}%)`);
}

// Show specific container state
function showState(state) {
    loadingContainer.classList.add("hidden");
    uploadContainer.classList.add("hidden");
    processingContainer.classList.add("hidden");
    completeContainer.classList.add("hidden");

    if (state === "loading") loadingContainer.classList.remove("hidden");
    else if (state === "upload") uploadContainer.classList.remove("hidden");
    else if (state === "processing") processingContainer.classList.remove("hidden");
    else if (state === "complete") completeContainer.classList.remove("hidden");
}

// Drag and drop event handlers
function setupDragAndDrop() {
    // Prevent default behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Add/remove visual cues
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    // Handle file inputs via button selection
    fileInput.addEventListener("change", (e) => {
        const files = e.target.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });
}

// Process selected file
function handleFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['mxl', 'xml', 'musicxml'].includes(ext)) {
        alert("지원되지 않는 파일 형식입니다. .mxl, .xml, .musicxml 파일만 업로드할 수 있습니다.");
        return;
    }

    currentFileName = file.name;
    log("System", `파일 업로드됨: ${file.name} (크기: ${(file.size / 1024).toFixed(1)} KB)`);

    showState("processing");

    // Read file bytes
    const reader = new FileReader();
    reader.onload = (e) => {
        const arrayBuffer = e.target.result;
        // Send arrayBuffer and name to Web Worker
        worker.postMessage({
            type: "process",
            data: {
                arrayBuffer: arrayBuffer,
                fileName: file.name
            }
        });
    };
    reader.readAsArrayBuffer(file);
}

// Handle annotated result returned from Worker
function handleResult(arrayBuffer, annotatedCount, totalCount) {
    log("System", `운지 계산 완료: 총 ${totalCount}개 음표 중 ${annotatedCount}개 표기 성공!`, "success-log");

    // Create download blob
    const blob = new Blob([arrayBuffer], { type: "application/vnd.recordare.musicxml+xml" });
    const url = URL.createObjectURL(blob);

    // Update download link
    const baseName = currentFileName.substring(0, currentFileName.lastIndexOf('.'));
    const ext = currentFileName.substring(currentFileName.lastIndexOf('.'));
    const outputName = `${baseName}_annotated${ext}`;

    downloadLink.href = url;
    downloadLink.download = outputName;
    
    resultSummary.textContent = `${currentFileName}의 총 ${totalCount}개 음표 중 ${annotatedCount}개에 대해 운지 및 줄 번호 표기가 완료되었습니다.`;

    showState("complete");
}

// Reset app state for another file
function resetApp() {
    fileInput.value = "";
    currentFileName = "";
    showState("upload");
    log("System", "새 악보 분석을 위해 업로드 대기 중...");
}
