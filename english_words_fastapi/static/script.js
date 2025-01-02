let currentWordIndex = 0;
let words = [];
const englishWord = document.getElementById('englishWord');
const russianWord = document.getElementById('russianWord');
const audioPlayer = document.getElementById('audioPlayer');
const nextWordBtn = document.getElementById('nextWordBtn');

async function fetchWords(telegramId, type) {
  let url;
  if (type === 'new') {
       url = `/new_words/${telegramId}`;
  }
  else {
       url = `/repeat_words/${telegramId}`;
  }
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        words = await response.json();
        loadWord();
    } catch (error) {
         englishWord.textContent = "Ошибка при загрузке слов";
        console.error("Error fetching words:", error);
    }
}

function loadWord() {
    if (currentWordIndex >= words.length) {
        nextWordBtn.disabled = true;
        return;
    }
    const currentWord = words[currentWordIndex];
    englishWord.textContent = currentWord.english;
    russianWord.textContent = currentWord.russian;
        if (currentWord.audio_path) {
        audioPlayer.src = currentWord.audio_path;
        audioPlayer.load();
        } else {
         audioPlayer.src = "";
         audioPlayer.load();
        }
    currentWordIndex++;
}

nextWordBtn.addEventListener('click', loadWord);

window.addEventListener('DOMContentLoaded', function() {
  const params = new URLSearchParams(window.location.search);
  const telegramId = params.get('telegram_id');
  const type = params.get('type');
  if (telegramId) {
    fetchWords(telegramId, type)
  } else {
    englishWord.textContent = "Ошибка: не передан telegram_id"
  }
});

audioPlayer.addEventListener('loadedmetadata', function() {
  this.play();
});
// let currentWordIndex = 0;
// let words = [];
// const englishWord = document.getElementById('englishWord');
// const russianWord = document.getElementById('russianWord');
// const audioPlayer = document.getElementById('audioPlayer');
// const nextWordBtn = document.getElementById('nextWordBtn');

// function loadWord() {
//     if (currentWordIndex >= words.length) {
//         nextWordBtn.disabled = true;
//         return;
//     }
//     const currentWord = words[currentWordIndex];
//     englishWord.textContent = currentWord.english;
//     russianWord.textContent = currentWord.russian;
//     if (currentWord.audio_path) {
//       audioPlayer.src = currentWord.audio_path;
//       audioPlayer.load();
//     } else {
//        audioPlayer.src = "";
//        audioPlayer.load();
//     }
//     currentWordIndex++;
// }
// nextWordBtn.addEventListener('click', loadWord);

// window.addEventListener('DOMContentLoaded', function() {
//     // Получаем JSON строку из query params
//     const params = new URLSearchParams(window.location.search);
//     const wordsParam = params.get('words');
//     try {
//         if (wordsParam) {
//              words = JSON.parse(wordsParam)
//              loadWord();
//         }
//         else {
//               englishWord.textContent = "Ошибка: Не переданы данные";
//         }
//     } catch (e) {
//         englishWord.textContent = "Ошибка при обработке данных";
//         console.error("Error processing words:", e);
//     }
// });

// audioPlayer.addEventListener('loadedmetadata', function() {
//   this.play();
// });

// let currentWordIndex = 0;
// let words = [];
// const englishWord = document.getElementById('englishWord');
// const russianWord = document.getElementById('russianWord');
// const audioPlayer = document.getElementById('audioPlayer');
// const nextWordBtn = document.getElementById('nextWordBtn');

// async function fetchWords(telegramId) {
//     try {
//         const response = await fetch(`/repeat_words/${telegramId}`);
//         if (!response.ok) {
//             throw new Error(`HTTP error! status: ${response.status}`);
//         }
//         words = await response.json();
//         loadWord();
//     } catch (error) {
//          englishWord.textContent = "Ошибка при загрузке слов";
//         console.error("Error fetching words:", error);
//     }
// }

// function loadWord() {
//     if (currentWordIndex >= words.length) {
//         nextWordBtn.disabled = true;
//         return;
//     }
//     const currentWord = words[currentWordIndex];
//     englishWord.textContent = currentWord.english;
//     russianWord.textContent = currentWord.russian;
//         if (currentWord.audio_path) {
//         audioPlayer.src = currentWord.audio_path;
//         audioPlayer.load();
//         } else {
//          audioPlayer.src = "";
//          audioPlayer.load();
//         }
//     currentWordIndex++;
// }

// nextWordBtn.addEventListener('click', loadWord);

// window.addEventListener('DOMContentLoaded', function() {
//   const params = new URLSearchParams(window.location.search);
//   const telegramId = params.get('telegram_id');
//   if (telegramId) {
//       fetchWords(telegramId)
//   } else {
//     englishWord.textContent = "Ошибка: не передан telegram_id"
//   }
// });

// audioPlayer.addEventListener('loadedmetadata', function() {
//   this.play();
// });