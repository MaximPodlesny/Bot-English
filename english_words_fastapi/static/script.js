let currentWordIndex = 0;
let words = [];
const englishWord = document.getElementById('englishWord');
const transcription = document.getElementById('transcription');
const russianWord = document.getElementById('russianWord');
const wordContainer = document.getElementById('wordContainer');
const audioPlayer = document.getElementById('audioPlayer');
const nextWordBtn = document.getElementById('nextWordBtn');
const playAudioButton = document.getElementById('playAudioButton');
let intervalId;
let progressBarElement;
let progressBarFill;
let progress = 100;
let isRepeat = false;
let isTranslationVisible = false;
let totalWordsToday = 0;
let learnedWords = 0;
let progressContainer = document.querySelector('.progress-container');

console.log("Script loaded.");

function handleWordData(data) {
    if (!data) {
        console.log("Получен пустой список слов");
        englishWord.textContent = "Вы изучили все имеющиеся слова";
        if (progressContainer) progressContainer.style.display = 'none'; // Скрываем progressContainer, если не было слов.
        return;
    }
    words = data;
    loadWord();
}

async function fetchWords(telegramId, type) {
    console.log("fetchWords called with telegramId:", telegramId, "and type:", type);
    let url;
    if (type === 'repeat') {
        url = `/repeat_words/${telegramId}`;
        isRepeat = true
    } else {
        url = `/new_words/${telegramId}`;
        isRepeat = false
    }
    try {
        console.log("Fetching data from:", url);
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log("Data received:", data);
        if (progressContainer) progressContainer.style.display = 'block';
        if (isRepeat) {
            handleWordData(data);
            resetProgressBar();
            console.log("Repeat mode. Reset progress bar.");
        } else {
            handleWordData(data.words);
            totalWordsToday = data.total_words_today;
            updateProgressBar();
            console.log("Learning mode. Updated progress bar.");
        }
    } catch (error) {
        englishWord.textContent = "Ошибка при загрузке слов";
        console.error("Error fetching words:", error);
    }
}


function updateProgressBar() {
    if (progressBarFill) {
        let progressPercent = 0;
        if (!isRepeat && totalWordsToday > 0 && words.length > 0) {
          learnedWords = currentWordIndex;
          progressPercent = (learnedWords / totalWordsToday) * 100;
        }
        
        progressBarFill.style.width = `${progressPercent}%`;
        console.log('Progress bar updated:', progressPercent);
        
    }
}


function resetProgressBar() {
    if (progressBarFill) {
        progressBarFill.style.width = '100%';
        console.log("Progress bar reset to 100%.");
    }
}

function startTimer() {
    if (!isRepeat) return;
    progress = 100;
    if (progressBarFill) {
        progressBarFill.style.width = '100%';
        console.log("Timer started. Progress bar set to 100%.");
    }
    clearInterval(intervalId);
    intervalId = setInterval(function () {
        progress -= 100 / 20;
        if (progressBarFill) {
            progressBarFill.style.width = progress + '%';
             console.log("Timer tick. Progress bar updated to:", progress + "%");
        }
        if (progress <= 0) {
            clearInterval(intervalId);
            loadWord();
            console.log("Timer expired. Loading next word.");
        }
    }, 100);
}
function stopTimer() {
    clearInterval(intervalId);
    console.log("Timer stopped.");
}


function loadWord() {
    stopTimer();
    if (russianWord) russianWord.style.display = 'none';
    if (transcription) transcription.style.display = 'none';
    if (playAudioButton) playAudioButton.style.display = 'none';
    isTranslationVisible = false;
    console.log("Loading word at index:", currentWordIndex);

    if (!words || currentWordIndex >= words.length) {
        if (isRepeat) {
            nextWordBtn.disabled = true;
            englishWord.textContent = "Повторение завершено";
            console.log("Repeat session finished.");
            if (progressContainer) progressContainer.style.display = 'none';
            return;
        } else {
            currentWordIndex = 0;
            englishWord.textContent = "Начинаем повторный показ";
           updateProgressBar();
           loadWord();
            console.log("Learning session finished. Starting repeat.");
            return;
        }
    }
    const currentWord = words[currentWordIndex];
    if (englishWord) englishWord.textContent = currentWord.english;
    if (!isRepeat) {
        if (transcription) {
             transcription.textContent = `${currentWord.transcription || ''}`;
            transcription.style.display = 'block';
        }
        if (russianWord) {
          russianWord.textContent = currentWord.russian;
          russianWord.style.display = 'block';
      }
        console.log("Learning word. Transcription and translation shown.");
    }

    if (currentWord.audio_path) {
      if (playAudioButton)  playAudioButton.style.display = 'inline-block';
        try {
            audioPlayer.src = `/static/${currentWord.audio_path}`;
            audioPlayer.load();
        } catch (error) {
            console.error("Error loading audio:", error);
            audioPlayer.src = "";
            audioPlayer.load();
           if (playAudioButton)  playAudioButton.style.display = 'none';
        }
    } else {
        audioPlayer.src = "";
        audioPlayer.load();
      if (playAudioButton) playAudioButton.style.display = 'none';
    }
    currentWordIndex++;
    if (!isRepeat) {
      updateProgressBar()
         console.log("Learning mode. Progress bar updated after load.");
   }
    if (isRepeat) {
        startTimer();
        console.log("Repeat mode. Timer started.");
    }
}

function toggleTranslation() {
    if (isRepeat) {
        if (isTranslationVisible) {
            if (russianWord) russianWord.style.display = 'none';
            if (transcription) transcription.style.display = 'none';
             if (playAudioButton) playAudioButton.style.display = 'none';
            isTranslationVisible = false;
            startTimer();
             console.log("Translation hidden. Timer started.");
        } else {
            stopTimer();
           const currentWord = words[currentWordIndex-1];
            if (russianWord) russianWord.style.display = 'block';
           if (transcription) {
                transcription.textContent = `${currentWord.transcription || ''}`;
                transcription.style.display = 'block';
           }
            if (currentWord.audio_path && playAudioButton) {
                playAudioButton.style.display = 'inline-block';
            }
            isTranslationVisible = true;
            console.log("Translation shown. Timer stopped.");
        }
    }
}

if (wordContainer) wordContainer.addEventListener('click', toggleTranslation);

if (nextWordBtn) nextWordBtn.addEventListener('click', function(event) {
    event.stopPropagation();
    loadWord();
});

if (playAudioButton) playAudioButton.addEventListener('click', function(event) {
    event.stopPropagation();
    audioPlayer.play();
});

window.addEventListener('DOMContentLoaded', function () {
   const params = new URLSearchParams(window.location.search);
   const telegramId = params.get('telegram_id');
   const type = params.get('type');
   if (telegramId) {
        fetchWords(telegramId, type);
    } else {
        englishWord.textContent = "Ошибка: не передан telegram_id";
    }
      progressBarFill = document.querySelector('.progress-fill');
      progressBarElement = document.querySelector('.progress-bar');
      updateProgressBar();
     if (words.length > 0) {
       loadWord()
      }
});

// let currentWordIndex = 0;
// let words = [];
// const englishWord = document.getElementById('englishWord');
// const transcription = document.getElementById('transcription');
// const russianWord = document.getElementById('russianWord');
// const wordContainer = document.getElementById('wordContainer');
// const audioPlayer = document.getElementById('audioPlayer');
// const nextWordBtn = document.getElementById('nextWordBtn');
// const playAudioButton = document.getElementById('playAudioButton');
// let intervalId;
// let progressBarElement = document.querySelector('.progress-bar');
// let progressBarFill = document.querySelector('.progress-fill');
// let progress = 100;
// let isRepeat = false;
// let isTranslationVisible = false;
// let totalWordsToday = 0;
// let learnedWords = 0;
// let progressContainer = document.querySelector('.progress-container');

// console.log("Script loaded.");

// function handleWordData(data) {
//    if(!data) {
//       console.log("Получен пустой список слов");
//       englishWord.textContent = "Вы изучили все имеющиеся слова";
//       progressContainer.style.display = 'none';
//       return
//     }

//     words = data;
//     loadWord();
// }
// async function fetchWords(telegramId, type) {
//     console.log("fetchWords called with telegramId:", telegramId, "and type:", type);
//     let url;
//      if (type === 'repeat') {
//         url = `/repeat_words/${telegramId}`;
//           isRepeat = true
//     } else {
//         url = `/new_words/${telegramId}`;
//         isRepeat = false
//     }
//     try {
//         console.log("Fetching data from:", url);
//         const response = await fetch(url);
//         if (!response.ok) {
//            throw new Error(`HTTP error! status: ${response.status}`);
//         }
//         const data = await response.json();
//         console.log("Data received:", data);
//           progressContainer.style.display = 'block';
//         if (isRepeat) {
//             handleWordData(data);
//             resetProgressBar();
//             console.log("Repeat mode. Reset progress bar.");
//         } else {
//             handleWordData(data.words);
//              totalWordsToday = data.total_words_today;
//             updateProgressBar();
//            console.log("Learning mode. Updated progress bar.");
//         }
//     } catch (error) {
//         englishWord.textContent = "Ошибка при загрузке слов";
//         console.error("Error fetching words:", error);
//     }
// }

// function updateProgressBar() {
//     if (!isRepeat && totalWordsToday > 0) {
//         learnedWords = currentWordIndex;
//         const progressPercent = (learnedWords / totalWordsToday) * 100;
//         progressBarFill.style.width = `${progressPercent}%`;
//          console.log("Progress bar updated to:", `${progressPercent}%`);
//    }
// }
// function resetProgressBar() {
//     progressBarFill.style.width = '100%';
//       console.log("Progress bar reset to 100%.");
// }
// function startTimer() {
//     if (!isRepeat) return;
//     progress = 100;
//      progressBarFill.style.width = '100%';
//      console.log("Timer started. Progress bar set to 100%.");
//     clearInterval(intervalId);
//     intervalId = setInterval(function () {
//         progress -= 100 / 20;
//          progressBarFill.style.width = progress + '%';
//            console.log("Timer tick. Progress bar updated to:", progress + "%");
//         if (progress <= 0) {
//             clearInterval(intervalId);
//             loadWord();
//               console.log("Timer expired. Loading next word.");
//         }
//     }, 100);
// }
// function stopTimer() {
//     clearInterval(intervalId);
//     console.log("Timer stopped.");
// }

// function loadWord() {
//     stopTimer();
//     russianWord.style.display = 'none';
//     transcription.style.display = 'none';
//     playAudioButton.style.display = 'none';
//     isTranslationVisible = false;
//      console.log("Loading word at index:", currentWordIndex);
//     if (!words || currentWordIndex >= words.length) {
//        if (isRepeat) {
//            nextWordBtn.disabled = true;
//             englishWord.textContent = "Повторение завершено";
//            console.log("Repeat session finished.");
//             progressContainer.style.display = 'none';
//             return;
//        } else {
//            currentWordIndex = 0;
//            englishWord.textContent = "Начинаем повторный показ";
//            updateProgressBar();
//            loadWord();
//            console.log("Learning session finished. Starting repeat.");
//             return;
//       }
//    }
//     const currentWord = words[currentWordIndex];
//     englishWord.textContent = currentWord.english;
//     if (!isRepeat) {
//         transcription.textContent = `${currentWord.transcription || ''}`;
//         transcription.style.display = 'block';
//          russianWord.textContent = currentWord.russian;
//         russianWord.style.display = 'block';
//            console.log("Learning word. Transcription and translation shown.");
//     }
//      if (currentWord.audio_path) {
//         playAudioButton.style.display = 'inline-block';
//         try {
//             audioPlayer.src = `/static/${currentWord.audio_path}`;
//             audioPlayer.load();
//         } catch (error) {
//             console.error("Error loading audio:", error);
//             audioPlayer.src = "";
//            audioPlayer.load();
//             playAudioButton.style.display = 'none';
//         }
//     } else {
//        audioPlayer.src = "";
//       audioPlayer.load();
//       playAudioButton.style.display = 'none';
//     }
//     currentWordIndex++;
//     if (!isRepeat) {
//         updateProgressBar()
//          console.log("Learning mode. Progress bar updated after load.");
//     }
//     if (isRepeat) {
//         startTimer();
//          console.log("Repeat mode. Timer started.");
//     }
// }

// function toggleTranslation() {
//     if (isRepeat) {
//         if (isTranslationVisible) {
//             russianWord.style.display = 'none';
//             transcription.style.display = 'none';
//            playAudioButton.style.display = 'none';
//             isTranslationVisible = false;
//             startTimer();
//               console.log("Translation hidden. Timer started.");
//         } else {
//             stopTimer();
//              const currentWord = words[currentWordIndex-1];
//             russianWord.style.display = 'block';
//             transcription.textContent = `${currentWord.transcription || ''}`;
//              transcription.style.display = 'block';
//             if (currentWord.audio_path) {
//                 playAudioButton.style.display = 'inline-block';
//             }
//             isTranslationVisible = true;
//             console.log("Translation shown. Timer stopped.");
//         }
//     }
// }

// wordContainer.addEventListener('click', toggleTranslation);

// nextWordBtn.addEventListener('click', function(event) {
//     event.stopPropagation();
//     loadWord();
// });

// playAudioButton.addEventListener('click', function(event) {
//     event.stopPropagation();
//     audioPlayer.play();
// });

// window.addEventListener('DOMContentLoaded', function() {
//     const params = new URLSearchParams(window.location.search);
//     const telegramId = params.get('telegram_id');
//     const type = params.get('type');
//     if (telegramId) {
//         fetchWords(telegramId, type);
//     } else {
//         englishWord.textContent = "Ошибка: не передан telegram_id";
//     }
// });

