/**
 * DOCUTRACE – Client-Side Interactions & Cryptographic Helpers
 */

document.addEventListener("DOMContentLoaded", () => {
    // ---------------- TAB NAVIGATION ---------------- //
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const tabId = btn.getAttribute("data-tab");
            
            // Toggle active tab buttons
            tabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            // Toggle active tab panes
            document.querySelectorAll(".tab-pane").forEach(pane => {
                pane.classList.remove("active");
                if (pane.id === tabId) {
                    pane.classList.add("active");
                }
            });
        });
    });

    // ---------------- FILE UPLOAD & PREVIEW ---------------- //
    const setupFileInput = (inputId, previewId, hashPreviewId = null) => {
        const fileInput = document.getElementById(inputId);
        const previewEl = document.getElementById(previewId);

        if (!fileInput || !previewEl) return;

        fileInput.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) {
                previewEl.style.display = "none";
                return;
            }

            const sizeInKb = (file.size / 1024).toFixed(1);
            const sizeStr = sizeInKb > 1024 ? (sizeInKb / 1024).toFixed(2) + " MB" : sizeInKb + " KB";

            previewEl.innerHTML = `
                <div style="display:flex; align-items:center; gap:0.75rem;">
                    <span style="font-size:1.5rem;">📄</span>
                    <div>
                        <div style="font-weight:600; color:#fff;">${file.name}</div>
                        <div style="font-size:0.8rem; color:#9ca3af;">Size: ${sizeStr} | Type: ${file.type || 'application/octet-stream'}</div>
                    </div>
                </div>
            `;
            previewEl.style.display = "block";

            // Instant Client-Side SHA-256 Preview using Web Crypto API
            if (hashPreviewId) {
                const hashEl = document.getElementById(hashPreviewId);
                if (hashEl) {
                    hashEl.innerHTML = `<span style="color:#38bdf8;">⚡ Computing client-side SHA-256 fingerprint...</span>`;
                    try {
                        const buffer = await file.arrayBuffer();
                        const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
                        const hashArray = Array.from(new Uint8Array(hashBuffer));
                        const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
                        hashEl.innerHTML = `
                            <div style="font-size:0.75rem; text-transform:uppercase; color:#9ca3af; margin-bottom:0.25rem;">Live Client-Computed SHA-256 Fingerprint:</div>
                            <div style="font-family:var(--font-mono); font-size:0.8rem; color:#34d399; word-break:break-all;">${hashHex}</div>
                        `;
                    } catch (err) {
                        hashEl.innerHTML = "";
                    }
                }
            }
        });
    };

    // Initialize dropzones
    setupFileInput("document_file", "upload_preview", "upload_hash_preview");
    setupFileInput("verify_file_input", "verify_preview", "verify_hash_preview");

    // ---------------- DRAG & DROP SUPPORT ---------------- //
    const dropzones = document.querySelectorAll(".dropzone");
    dropzones.forEach(zone => {
        ['dragenter', 'dragover'].forEach(eventName => {
            zone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.remove('dragover');
            }, false);
        });

        zone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            const fileInput = zone.querySelector('input[type="file"]');
            if (fileInput && files.length > 0) {
                fileInput.files = files;
                const changeEvent = new Event('change');
                fileInput.dispatchEvent(changeEvent);
            }
        });
    });

    // ---------------- COPY TO CLIPBOARD ---------------- //
    window.copyToClipboard = (text, btnElement) => {
        navigator.clipboard.writeText(text).then(() => {
            const originalText = btnElement.innerText;
            btnElement.innerText = "✓ Copied!";
            btnElement.style.background = "#10b981";
            btnElement.style.color = "#ffffff";
            setTimeout(() => {
                btnElement.innerText = originalText;
                btnElement.style.background = "";
                btnElement.style.color = "";
            }, 2000);
        }).catch(err => {
            console.error("Copy failed", err);
        });
    };

    // ---------------- LIVE BLOCKCHAIN INTEGRITY AUDIT ---------------- //
    const checkChainBtn = document.getElementById("btn-audit-blockchain");
    if (checkChainBtn) {
        checkChainBtn.addEventListener("click", async () => {
            const statusBox = document.getElementById("blockchain-audit-status");
            checkChainBtn.disabled = true;
            checkChainBtn.innerText = "Auditing cryptographic links...";

            try {
                const response = await fetch("/api/validate-chain");
                const data = await response.json();

                if (statusBox) {
                    statusBox.style.display = "block";
                    if (data.is_valid) {
                        statusBox.className = "alert alert-success";
                        statusBox.innerHTML = `<strong>✓ VALID:</strong> ${data.message} (Chain Height: ${data.chain_length} blocks, Proof-of-Work verified).`;
                    } else {
                        statusBox.className = "alert alert-danger";
                        statusBox.innerHTML = `<strong>⚠ TAMPER ALERT:</strong> ${data.message}`;
                    }
                }
            } catch (error) {
                if (statusBox) {
                    statusBox.style.display = "block";
                    statusBox.className = "alert alert-danger";
                    statusBox.innerText = "Failed to communicate with Blockchain validation API.";
                }
            } finally {
                checkChainBtn.disabled = false;
                checkChainBtn.innerText = "Run Cryptographic Audit";
            }
        });
    }

    // ---------------- TABLE SEARCH / FILTER ---------------- //
    const searchInput = document.getElementById("table-search-input");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            const term = e.target.value.toLowerCase();
            const rows = document.querySelectorAll(".data-table tbody tr");
            rows.forEach(row => {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(term) ? "" : "none";
            });
        });
    }
});
