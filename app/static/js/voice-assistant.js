/**
 * Adopt Me - AI Voice Navigation Assistant
 * A production-ready, singleton voice assistant utilizing Web Speech API and SpeechSynthesis.
 */

(function () {
    // 1. PREVENT DUPLICATE INITIALIZATION (Singleton Pattern)
    if (window.__adoptMeVoiceAssistantInitialized) {
        console.warn("Voice Assistant already initialized. Skipping duplicate init.");
        return;
    }
    window.__adoptMeVoiceAssistantInitialized = true;

    class VoiceAssistant {
        // ==========================================
        // 1. CONSTRUCTOR
        // ==========================================
        constructor() {
            // State
            this.isListening = false;
            this.isProcessing = false;
            this.isSpeaking = false;
            this.lastCommandTime = 0;
            this.cooldownMs = 2000; // Debounce threshold
            this.currentTranscript = '';

            // LocalStorage Persistence
            this.prefs = this.loadPreferences();

            // DOM Elements
            this.btn = document.getElementById('ai-voice-btn');
            this.btnIcon = document.getElementById('ai-voice-btn-icon');
            this.pulse = document.getElementById('ai-voice-pulse');
            this.statusPopup = document.getElementById('ai-voice-status');
            this.statusTitle = document.getElementById('ai-voice-title');
            this.statusText = document.getElementById('ai-voice-text');
            this.statusIcon = document.getElementById('ai-voice-icon-container');

            // Timeout references
            this.popupTimeout = null;
            this.silenceTimeout = null;

            // Speech APIs
            this.recognition = null;
            this.synth = window.speechSynthesis;

            // Centralized Command Architecture (Filters, Scroll, Utility)
            const filler = "(?:\\s+(?:to|me|the|please|for|page))*\\s*";
            this.COMMANDS = {
                filters: [
                    { regex: /\b(?:adopt a dog|available dogs|dogs for adoption|dogs?)\b/i, action: () => this.applyFilter('type', 'dog', "Showing dogs for adoption.") },
                    { regex: /\b(?:adopt a cat|available cats|cats for adoption|cats?)\b/i, action: () => this.applyFilter('type', 'cat', "Showing cats for adoption.") },
                    { regex: new RegExp(`(?:show|find|looking for)?${filler}(?:male dogs?)`, 'i'), action: () => this.applyFilter({ type: 'dog', gender: 'Male' }, null, "Showing male dogs.") },
                    { regex: new RegExp(`(?:show|find|looking for)?${filler}(?:female dogs?)`, 'i'), action: () => this.applyFilter({ type: 'dog', gender: 'Female' }, null, "Showing female dogs.") },
                    { regex: new RegExp(`(?:show|find|looking for)?${filler}(?:male cats?)`, 'i'), action: () => this.applyFilter({ type: 'cat', gender: 'Male' }, null, "Showing male cats.") },
                    { regex: new RegExp(`(?:show|find|looking for)?${filler}(?:female cats?)`, 'i'), action: () => this.applyFilter({ type: 'cat', gender: 'Female' }, null, "Showing female cats.") },
                    { regex: new RegExp(`(?:clear|reset|remove)\\s*(?:filters?)|show all`, 'i'), action: () => this.applyFilter(null, null, "Clearing filters.") }
                ],
                scroll: [
                    { regex: /(?:scroll|go)\s*(?:down)/i, action: () => this.scroll(window.innerHeight * 0.8, "Scrolling down.") },
                    { regex: /(?:scroll|go)\s*(?:up)/i, action: () => this.scroll(-window.innerHeight * 0.8, "Scrolling up.") },
                    { regex: /(?:go to|scroll to)\s*(?:top)/i, action: () => { window.scrollTo({ top: 0, behavior: 'smooth' }); this.speak("Going to top."); } },
                    { regex: /(?:go to|scroll to)\s*(?:bottom)/i, action: () => { window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); this.speak("Going to bottom."); } }
                ],
                utility: [
                    { regex: /(?:mute|quiet|stop talking)/i, action: () => this.toggleMute(true) },
                    { regex: /(?:unmute|speak|talk)/i, action: () => this.toggleMute(false) },
                    { regex: /(?:hello|hi|hey)\b/i, action: () => { this.showPopup("Hello!", "How can I help you adopt a pet today?"); this.speak("Hello! How can I help you adopt a pet today?"); } },
                    { regex: new RegExp(`(?:go back|return|back)`, 'i'), action: () => this.goBack() }
                ]
            };

            this.init();
        }

        // ==========================================
        // 2. INITIALIZATION METHODS
        // ==========================================

        loadPreferences() {
            try {
                const prefs = localStorage.getItem('adoptme_voice_prefs');
                return prefs ? JSON.parse(prefs) : { muted: false, enabled: true };
            } catch (e) {
                return { muted: false, enabled: true };
            }
        }

        savePreferences() {
            try {
                localStorage.setItem('adoptme_voice_prefs', JSON.stringify(this.prefs));
            } catch (e) {
                console.error("Could not save preferences", e);
            }
        }

        init() {
            if (!this.btn || !this.statusPopup) return;

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                this.btn.style.display = 'none';
                console.warn("Speech Recognition API is not supported in this browser.");
                return;
            }

            this.recognition = new SpeechRecognition();
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';

            this.btn.addEventListener('click', () => this.toggleListening());
            this.btn.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleListening();
                }
            });

            this.recognition.onstart = () => this.handleStart();
            this.recognition.onresult = (e) => this.handleResult(e);
            this.recognition.onerror = (e) => this.handleError(e);
            this.recognition.onend = () => this.handleEnd();

            window.addEventListener('beforeunload', () => {
                if (this.isListening) {
                    this.recognition.stop();
                }
                this.synth.cancel();
            });
        }

        // ==========================================
        // 3. RECOGNITION LIFECYCLE METHODS
        // ==========================================

        toggleListening() {
            if (this.isProcessing || this.isSpeaking) return;

            if (this.isListening) {
                this.recognition.stop();
            } else {
                try {
                    this.recognition.start();
                } catch (e) {
                    console.error("Recognition start error:", e);
                    this.resetState();
                }
            }
        }

        handleStart() {
            this.isListening = true;
            this.currentTranscript = '';
            this.updateUI('listening');
            this.showPopup("Listening...", "Say a command like 'Open pets' or 'Scroll down'");
        }

        handleResult(event) {
            let transcriptParts = [];
            for (let i = 0; i < event.results.length; ++i) {
                transcriptParts.push(event.results[i][0].transcript.trim());
            }
            this.currentTranscript = transcriptParts.join(' ');

            this.showPopup("Listening...", `"${this.currentTranscript}"`);

            clearTimeout(this.silenceTimeout);
            this.silenceTimeout = setTimeout(() => {
                this.processTranscript();
            }, 1200);
        }

        processTranscript() {
            if (!this.currentTranscript || this.isProcessing) return;

            const textToProcess = this.currentTranscript;
            this.currentTranscript = '';
            clearTimeout(this.silenceTimeout);

            this.isProcessing = true;
            this.updateUI('processing');
            if (this.isListening) {
                this.recognition.stop();
            }

            const now = Date.now();
            if (now - this.lastCommandTime < this.cooldownMs) {
                console.log("Command ignored (cooldown)");
                this.resetState();
                return;
            }
            this.lastCommandTime = now;

            console.log("Recognized Transcript:", textToProcess);
            this.parseCommand(textToProcess);
        }

        handleError(event) {
            this.currentTranscript = '';
            clearTimeout(this.silenceTimeout);
            this.resetState();

            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                this.showPopup("Microphone Blocked", "Please allow microphone access to use voice features.", true);
            } else if (event.error === 'no-speech') {
                this.showPopup("No Speech Detected", "I didn't hear anything. Try again.");
            } else {
                this.showPopup("Error", `An error occurred: ${event.error}`, true);
            }
        }

        handleEnd() {
            this.isListening = false;
            if (!this.isProcessing && this.currentTranscript) {
                clearTimeout(this.silenceTimeout);
                this.processTranscript();
            } else if (!this.isProcessing) {
                this.resetState();
            }
        }

        // ==========================================
        // 4. PARSING METHODS
        // ==========================================

        parseCommand(rawTranscript) {
            const transcript = this.normalizeVoiceText(rawTranscript);

            // STEP 1: Try Dynamic DOM Matching
            const clicked = this.findClickableElementByVoice(transcript);
            if (clicked) {
                return; // Handled by DOM click
            }

            // STEP 2: Try Route Navigation Fallback
            const routeMatched = this.tryRouteNavigation(transcript);
            if (routeMatched) {
                return;
            }

            // STEP 3: Try Manual Commands (Filters, Scroll, Utility)
            let matchedManual = false;
            for (const category in this.COMMANDS) {
                if (matchedManual) break;
                for (const cmd of this.COMMANDS[category]) {
                    if (cmd.regex.test(transcript)) {
                        console.log("Matched Command Category:", category, "Regex:", cmd.regex);
                        this.showPopup("Command Recognized", `[${category}] ${transcript}`);
                        cmd.action();
                        matchedManual = true;
                        break;
                    }
                }
            }

            if (matchedManual) {
                return;
            }

            // STEP 4: Unknown Command
            console.log("No match found for:", transcript);
            this.showPopup("Unknown Command", "Sorry, I didn't understand that.");
            this.speak("Sorry, I didn't understand that.");
            // this.resetState() is handled by speak() onend event
        }

        tryRouteNavigation(transcript) {
            // Intelligent Route Mapping based on Flask pages
            const routes = {
                'home': '/',
                'front page': '/',
                'dashboard': '/dashboard',
                'about': '/about',
                'profile': '/profile',
                'owner dashboard': '/owner-dashboard',
                'post a pet': '/add-pet',
                'add pet': '/add-pet',
                'categories': '/choose-category',
                'pets': '/pets',
                'catalog': '/pets',
                'animals': '/pets',
                'favorites': '/favorites',
                'my pets': '/my-pets',
                'applications': '/notifications',
                'notifications': '/notifications',
                'login': '/login',
                'sign in': '/login',
                'register': '/register',
                'sign up': '/register',
                'create account': '/register',
                'admin': '/admin',
                'admin dashboard': '/admin'
            };

            for (const [key, path] of Object.entries(routes)) {
                if (transcript.includes(key)) {
                    if (window.location.pathname === path) {
                        this.showPopup("Already Here", `You are already on the ${key} page.`);
                        this.speak(`You are already on the ${key} page.`);
                        this.resetState();
                    } else {
                        this.navigate(path, `Opening ${key}.`);
                    }
                    return true;
                }
            }
            return false;
        }

        // ==========================================
        // 5. COMMAND ACTION METHODS
        // ==========================================

        navigate(url, spokenMessage) {
            console.log("Navigation Target:", url);
            this.speak(spokenMessage);
            setTimeout(() => {
                this.resetState();
                window.location.href = url;
            }, 800);
        }

        goBack() {
            this.speak("Going back.");
            setTimeout(() => {
                this.resetState();
                window.history.back();
            }, 800);
        }

        applyFilter(keyOrObj, value, spokenMessage) {
            this.speak(spokenMessage);

            setTimeout(() => {
                this.resetState();
                const currentPath = window.location.pathname;
                if (currentPath !== '/pets') {
                    let query = '?';
                    if (keyOrObj === null) {
                        query = ''; // clear filters
                    } else if (typeof keyOrObj === 'object') {
                        query += new URLSearchParams(keyOrObj).toString();
                    } else {
                        query += `${keyOrObj}=${value}`;
                    }
                    window.location.href = `/pets${query}`;
                } else {
                    const url = new URL(window.location);

                    if (keyOrObj === null) {
                        window.location.href = '/pets';
                        return;
                    }

                    if (typeof keyOrObj === 'object') {
                        for (const k in keyOrObj) {
                            url.searchParams.set(k, keyOrObj[k]);
                        }
                    } else {
                        url.searchParams.set(keyOrObj, value);
                    }
                    window.location.href = url.toString();
                }
            }, 800);
        }

        scroll(amount, spokenMessage) {
            this.speak(spokenMessage);
            window.scrollBy({ top: amount, left: 0, behavior: 'smooth' });
            this.resetState();
        }

        toggleMute(mute) {
            this.prefs.muted = mute;
            this.savePreferences();
            const msg = mute ? "Voice feedback muted." : "Voice feedback enabled.";
            this.showPopup("Settings Updated", msg);
            if (!mute) {
                this.speak(msg);
            }
            this.resetState();
        }

        // ==========================================
        // 6. DOM SCANNING & INTERACTION METHODS
        // ==========================================

        normalizeVoiceText(text) {
            // Remove punctuation and extra spaces, lowercase
            let normalized = text.toLowerCase()
                .replace(/[.,!?]/g, '')
                .replace(/\s+/g, ' ')
                .trim();

            // Strip out common action phrases from the beginning
            const actionPhrases = [
                'click on', 'click', 'open up', 'open', 'go to',
                'navigate to', 'press', 'select', 'show me', 'show',
                'take me to', 'browse', 'search for', 'find', 'looking for'
            ];

            for (let phrase of actionPhrases) {
                if (normalized.startsWith(phrase + ' ')) {
                    normalized = normalized.substring(phrase.length + 1).trim();
                    break; // Strip only the first matching action word
                } else if (normalized === phrase) {
                    // Prevent returning empty if they just said "click"
                    break;
                }
            }

            return normalized;
        }

        isElementInteractable(el) {
            // Check basic attributes
            if (el.disabled || el.getAttribute('aria-hidden') === 'true') {
                return false;
            }

            // Check visibility styles
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                return false;
            }

            // Check if element has zero dimensions (collapsed)
            if (el.offsetWidth === 0 && el.offsetHeight === 0) {
                return false;
            }

            return true;
        }

        isProtectedAction(el, textContent) {
            const protectedKeywords = ['delete', 'remove', 'logout', 'sign out', 'reject'];
            const lowerText = textContent.toLowerCase();

            for (let kw of protectedKeywords) {
                if (lowerText.includes(kw)) {
                    return true;
                }
            }
            return false;
        }

        getAllInteractiveElements() {
            // Scan live DOM for elements
            const selectors = 'button, a, [role="button"], .btn, [onclick], .cursor-pointer';
            return Array.from(document.querySelectorAll(selectors));
        }

        scoreVoiceMatch(voiceText, el) {
            let score = 0;

            const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase().trim();
            const ariaLabelledBy = el.getAttribute('aria-labelledby');
            let labelledByText = '';
            if (ariaLabelledBy) {
                const labelEl = document.getElementById(ariaLabelledBy);
                if (labelEl) labelledByText = labelEl.innerText.toLowerCase().trim();
            }

            const visibleText = (el.innerText || el.textContent || '').toLowerCase().trim();
            const titleAttr = (el.getAttribute('title') || '').toLowerCase().trim();

            // Aggregate all text representations to match against
            const elementTexts = [
                { text: ariaLabel, weight: 1.0 },
                { text: labelledByText, weight: 1.0 },
                { text: visibleText, weight: 0.9 },
                { text: titleAttr, weight: 0.8 }
            ].filter(t => t.text.length > 0);

            if (elementTexts.length === 0) return 0; // Icon-only without label

            let bestMatchScore = 0;

            for (let target of elementTexts) {
                let currentScore = 0;

                if (target.text === voiceText) {
                    currentScore = 100 * target.weight; // Exact match
                } else if (target.text.includes(voiceText)) {
                    // Partial match (voice text is inside element text)
                    // Bonus for shorter text (less extra words)
                    currentScore = (50 + (voiceText.length / target.text.length) * 30) * target.weight;
                } else if (voiceText.includes(target.text)) {
                    // Partial match (element text is fully inside voice text)
                    currentScore = 70 * target.weight;
                } else {
                    // Fuzzy overlap (words matching)
                    const voiceWords = voiceText.split(' ');
                    const targetWords = target.text.split(' ');
                    let matchCount = 0;
                    for (let vw of voiceWords) {
                        if (targetWords.includes(vw)) matchCount++;
                    }
                    if (matchCount > 0) {
                        currentScore = (30 * (matchCount / Math.max(voiceWords.length, targetWords.length))) * target.weight;
                    }
                }

                if (currentScore > bestMatchScore) {
                    bestMatchScore = currentScore;
                }
            }

            if (bestMatchScore === 0) return 0;

            // Element Type Multipliers
            const tagName = el.tagName.toLowerCase();
            if (tagName === 'button' || tagName === 'a') bestMatchScore *= 1.1; // Native priority
            if (el.classList.contains('bg-brand-primary') || el.classList.contains('bg-[#ff5e1c]')) bestMatchScore *= 1.1; // CTA priority

            // Viewport Visibility Priority
            const rect = el.getBoundingClientRect();
            const inViewport = (rect.top >= 0 && rect.bottom <= window.innerHeight);
            if (inViewport) bestMatchScore *= 1.2;

            return bestMatchScore;
        }

        findClickableElementByVoice(transcript) {
            const elements = this.getAllInteractiveElements();
            let bestElement = null;
            let highestScore = 0;

            for (const el of elements) {
                if (!this.isElementInteractable(el)) continue;

                const score = this.scoreVoiceMatch(transcript, el);
                if (score > highestScore) {
                    highestScore = score;
                    bestElement = el;
                }
            }

            // Confidence Threshold System
            if (highestScore < 40) {
                return false; // Not confident enough, proceed to route fallback
            }

            if (bestElement) {
                const visibleText = (bestElement.innerText || bestElement.getAttribute('aria-label') || 'element').trim();

                if (this.isProtectedAction(bestElement, visibleText)) {
                    this.showPopup("Protected Action", `I cannot auto-click "${visibleText}". Please click it manually.`, true);
                    this.speak(`I cannot safely click ${visibleText} for you. Please confirm it manually.`);
                    this.resetState();
                    return true; // Handled
                }

                console.log(`Matched DOM Element: Score ${highestScore.toFixed(1)}`, bestElement);
                this.showPopup("Interactive Command", `Selecting "${visibleText}"`);
                this.speak(`Selecting ${visibleText}.`);

                // Visual Preview & Accessibility Focus
                bestElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

                bestElement.classList.add(
                    'ring-4',
                    'ring-brand-accent',
                    'scale-105',
                    'transition-all',
                    'duration-300',
                    'z-50',
                    'relative'
                );

                setTimeout(() => {
                    bestElement.classList.remove(
                        'ring-4',
                        'ring-brand-accent',
                        'scale-105',
                        'z-50',
                        'relative'
                    );

                    bestElement.focus();

                    requestAnimationFrame(() => {
                        try {
                            bestElement.click();
                        } catch (err) {
                            console.error("Click execution failed:", err);
                        }
                        this.resetState();
                    });
                }, 400); // Wait ~400ms for visual preview

                return true;
            }

            return false;
        }

        // ==========================================
        // 7. SPEECH SYNTHESIS METHODS
        // ==========================================

        speak(text) {
            if (!text || this.prefs.muted) {
                this.resetState();
                return;
            }

            let wasListening = this.isListening;
            if (wasListening) {
                this.recognition.stop();
            }

            this.synth.cancel();
            const utterance = new SpeechSynthesisUtterance(text);

            this.isSpeaking = true;

            utterance.onend = () => {
                this.isSpeaking = false;
                this.resetState();
            };

            utterance.onerror = () => {
                this.isSpeaking = false;
                this.resetState();
            };

            this.synth.speak(utterance);
        }

        // ==========================================
        // 8. UI METHODS
        // ==========================================

        updateUI(state) {
            let iconName = 'mic';
            let iconClass = 'w-6 h-6';

            if (state === 'listening') {
                this.pulse.classList.add('animate-ping', 'opacity-75');
                this.pulse.classList.remove('opacity-0', 'group-hover:opacity-20');
                iconName = 'mic';
            } else {
                this.pulse.classList.remove('animate-ping', 'opacity-75');
                this.pulse.classList.add('opacity-0', 'group-hover:opacity-20');
            }

            if (state === 'processing') {
                iconName = 'loader';
                iconClass += ' animate-spin';
            } else if (state === 'error') {
                iconName = 'mic-off';
                this.btn.classList.add('bg-brand-danger');
                this.btn.classList.remove('bg-brand-primary', 'hover:bg-[#006a78]');

                setTimeout(() => {
                    this.btn.classList.remove('bg-brand-danger');
                    this.btn.classList.add('bg-brand-primary', 'hover:bg-[#006a78]');
                }, 3000);
            }

            this.btnIcon.innerHTML = `<i data-lucide="${iconName}" class="${iconClass}"></i>`;
            if (window.lucide) {
                window.lucide.createIcons({
                    root: this.btnIcon
                });
            }
        }

        showPopup(title, text, isError = false) {
            clearTimeout(this.popupTimeout);

            this.statusTitle.textContent = title;
            this.statusText.textContent = text;

            if (isError) {
                this.statusTitle.classList.add('text-brand-danger');
                this.statusTitle.classList.remove('text-brand-text');
                this.statusIcon.innerHTML = '<i data-lucide="alert-circle" class="w-5 h-5 text-brand-danger"></i>';
            } else {
                this.statusTitle.classList.remove('text-brand-danger');
                this.statusTitle.classList.add('text-brand-text');
                this.statusIcon.innerHTML = '<i data-lucide="bot" class="w-5 h-5 text-brand-primary"></i>';
            }

            if (window.lucide) {
                window.lucide.createIcons({ root: this.statusIcon });
            }

            this.statusPopup.classList.remove('opacity-0', 'translate-y-4', 'pointer-events-none');
            this.statusPopup.classList.add('opacity-100', 'translate-y-0');

            if (!this.isProcessing) {
                this.hidePopup(4000);
            }
        }

        hidePopup(delay = 0) {
            clearTimeout(this.popupTimeout);
            this.popupTimeout = setTimeout(() => {
                this.statusPopup.classList.add('opacity-0', 'translate-y-4', 'pointer-events-none');
                this.statusPopup.classList.remove('opacity-100', 'translate-y-0');
            }, delay);
        }

        // ==========================================
        // 9. UTILITY / RESET METHODS
        // ==========================================

        resetState() {
            this.isProcessing = false;
            this.isListening = false;
            this.updateUI('idle');
            this.hidePopup(2000);
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        window.AdoptMeAssistant = new VoiceAssistant();
    });

})();
