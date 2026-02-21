const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreElement = document.getElementById('score');
const highScoreElement = document.getElementById('high-score');
const difficultyInput = document.getElementById('difficulty');
const difficultyValue = document.getElementById('difficulty-value');
const gameOverScreen = document.getElementById('game-over-screen');
const startScreen = document.getElementById('start-screen');
const finalScoreElement = document.getElementById('final-score');
const restartBtn = document.getElementById('restart-btn');
const startBtn = document.getElementById('start-btn');

// Audio Context setup for synthesized sounds
const AudioContext = window.AudioContext || window.webkitAudioContext;
const audioCtx = new AudioContext();

// Game constants
const GRID_SIZE = 20;
const TILE_COUNT = canvas.width / GRID_SIZE;

// Game state
let score = 0;
let highScore = localStorage.getItem('snakeHighScore') || 0;
let snake = [];
let food = { x: 0, y: 0 };
let dx = 0;
let dy = 0;
let inputQueue = [];
let gameLoop;
let isGameRunning = false;
let speed = 100; // Default speed (ms per frame)
let difficulty = 5;

// Initialize high score display
highScoreElement.textContent = highScore;

// Event Listeners
document.addEventListener('keydown', handleKeydown);
difficultyInput.addEventListener('input', updateDifficulty);
restartBtn.addEventListener('click', startGame);
startBtn.addEventListener('click', startGame);

// --- Audio Functions ---
function playEatSound() {
    if (audioCtx.state === 'suspended') audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    
    osc.type = 'sine';
    osc.frequency.setValueAtTime(800, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1200, audioCtx.currentTime + 0.1);
    
    gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.1);
    
    osc.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    
    osc.start();
    osc.stop(audioCtx.currentTime + 0.1);
}

function playGameOverSound() {
    if (audioCtx.state === 'suspended') audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(300, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(50, audioCtx.currentTime + 0.5);
    
    gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);
    
    osc.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    
    osc.start();
    osc.stop(audioCtx.currentTime + 0.5);
}
// -----------------------

function updateDifficulty() {
    difficulty = parseInt(difficultyInput.value);
    difficultyValue.textContent = difficulty;
    // Map difficulty 1-10 to speed (slower to faster)
    // Level 1: 200ms, Level 10: 20ms
    speed = 220 - (difficulty * 20);
}

function initGame() {
    snake = [
        { x: 10, y: 10 },
        { x: 9, y: 10 },
        { x: 8, y: 10 }
    ];
    score = 0;
    dx = 1;
    dy = 0;
    inputQueue = [];
    scoreElement.textContent = score;
    updateDifficulty();
    createFood();
    gameOverScreen.classList.add('hidden');
    startScreen.classList.add('hidden');
    isGameRunning = true;
}

function startGame() {
    // Resume audio context on user interaction (required by browsers)
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    
    if (gameLoop) clearInterval(gameLoop);
    initGame();
    gameLoop = setInterval(drawGame, speed);
}

function drawGame() {
    if (!isGameRunning) return;

    // Process one valid input from the queue per frame
    while (inputQueue.length > 0) {
        const key = inputQueue.shift();
        const goingUp = dy === -1;
        const goingDown = dy === 1;
        const goingRight = dx === 1;
        const goingLeft = dx === -1;

        let newDx = dx;
        let newDy = dy;

        if (key === 'ArrowLeft' && !goingRight) {
            newDx = -1; newDy = 0;
        } else if (key === 'ArrowUp' && !goingDown) {
            newDx = 0; newDy = -1;
        } else if (key === 'ArrowRight' && !goingLeft) {
            newDx = 1; newDy = 0;
        } else if (key === 'ArrowDown' && !goingUp) {
            newDx = 0; newDy = 1;
        }

        // If the key resulted in a valid direction change, apply it and break
        if (newDx !== dx || newDy !== dy) {
            dx = newDx;
            dy = newDy;
            break;
        }
    }

    moveSnake();
    
    if (checkGameOver()) {
        endGame();
        return;
    }

    clearCanvas();
    drawFood();
    drawSnake();
}

function clearCanvas() {
    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function drawSnake() {
    snake.forEach((part, index) => {
        // Head is a slightly different color
        if (index === 0) {
            ctx.fillStyle = '#66bb6a';
        } else {
            ctx.fillStyle = '#4CAF50';
        }
        
        ctx.fillRect(part.x * GRID_SIZE, part.y * GRID_SIZE, GRID_SIZE - 2, GRID_SIZE - 2);
        
        // Add eyes to the head
        if (index === 0) {
            ctx.fillStyle = 'white';
            
            // Simple logic to place eyes roughly correct
            const eyeSize = 4;
            const offset = 4;
            
            if (dx === 1) { // Moving Right
                ctx.fillRect(part.x * GRID_SIZE + GRID_SIZE - offset - eyeSize, part.y * GRID_SIZE + offset, eyeSize, eyeSize);
                ctx.fillRect(part.x * GRID_SIZE + GRID_SIZE - offset - eyeSize, part.y * GRID_SIZE + GRID_SIZE - offset - eyeSize, eyeSize, eyeSize);
            } else if (dx === -1) { // Moving Left
                ctx.fillRect(part.x * GRID_SIZE + offset, part.y * GRID_SIZE + offset, eyeSize, eyeSize);
                ctx.fillRect(part.x * GRID_SIZE + offset, part.y * GRID_SIZE + GRID_SIZE - offset - eyeSize, eyeSize, eyeSize);
            } else if (dy === -1) { // Moving Up
                ctx.fillRect(part.x * GRID_SIZE + offset, part.y * GRID_SIZE + offset, eyeSize, eyeSize);
                ctx.fillRect(part.x * GRID_SIZE + GRID_SIZE - offset - eyeSize, part.y * GRID_SIZE + offset, eyeSize, eyeSize);
            } else if (dy === 1) { // Moving Down
                ctx.fillRect(part.x * GRID_SIZE + offset, part.y * GRID_SIZE + GRID_SIZE - offset - eyeSize, eyeSize, eyeSize);
                ctx.fillRect(part.x * GRID_SIZE + GRID_SIZE - offset - eyeSize, part.y * GRID_SIZE + GRID_SIZE - offset - eyeSize, eyeSize, eyeSize);
            }
        }
    });
}

function drawFood() {
    ctx.fillStyle = '#ff5252';
    // Draw food as a circle
    ctx.beginPath();
    ctx.arc(
        food.x * GRID_SIZE + GRID_SIZE/2, 
        food.y * GRID_SIZE + GRID_SIZE/2, 
        GRID_SIZE/2 - 2, 
        0, 
        2 * Math.PI
    );
    ctx.fill();
}

function moveSnake() {
    const head = { x: snake[0].x + dx, y: snake[0].y + dy };
    snake.unshift(head);

    if (head.x === food.x && head.y === food.y) {
        score += 10 * difficulty; // Higher difficulty gives more points
        scoreElement.textContent = score;
        playEatSound(); // Play sound when eating
        createFood();
    } else {
        snake.pop();
    }
}

function createFood() {
    let validFood = false;
    while (!validFood) {
        food = {
            x: Math.floor(Math.random() * TILE_COUNT),
            y: Math.floor(Math.random() * TILE_COUNT)
        };

        validFood = true;
        // Make sure food doesn't spawn on snake
        for (let part of snake) {
            if (part.x === food.x && part.y === food.y) {
                validFood = false;
                break;
            }
        }
    }
}

function handleKeydown(event) {
    const key = event.key;
    
    // Prevent default scrolling for arrow keys
    if(["ArrowUp","ArrowDown","ArrowLeft","ArrowRight"].indexOf(key) > -1) {
        event.preventDefault();
        
        // Add to input queue if it's not full and not the same as the last key
        if (inputQueue.length === 0 || inputQueue[inputQueue.length - 1] !== key) {
            if (inputQueue.length < 3) {
                inputQueue.push(key);
            }
        }
    }
}

function checkGameOver() {
    const head = snake[0];

    // Wall collision
    if (head.x < 0 || head.x >= TILE_COUNT || head.y < 0 || head.y >= TILE_COUNT) {
        return true;
    }

    // Self collision
    for (let i = 1; i < snake.length; i++) {
        if (head.x === snake[i].x && head.y === snake[i].y) {
            return true;
        }
    }

    return false;
}

function endGame() {
    isGameRunning = false;
    clearInterval(gameLoop);
    
    playGameOverSound(); // Play sound on game over
    
    if (score > highScore) {
        highScore = score;
        localStorage.setItem('snakeHighScore', highScore);
        highScoreElement.textContent = highScore;
    }
    
    finalScoreElement.textContent = score;
    gameOverScreen.classList.remove('hidden');
}
