let imageData = [
];
for (let i = 0; i <= 28; i++) {
    imageData.push({
        src: `/static/images/${i}.jpg`,
    });
}

const gallery = document.getElementById('gallery');
let currentSpreadIndex = 0;
let isAnimating = false;
let autoTurnEnabled = true;
let autoTurnInterval = null;
const AUTO_TURN_DELAY = 5000; // 3 seconds between turns

function initGallery() {
    const spreadCount = Math.ceil(imageData.length / 2);
    
    for (let i = 0; i < spreadCount; i++) {
        const spreadContainer = document.createElement('div');
        spreadContainer.className = 'spread-container';
        spreadContainer.style.display = i === 0 ? 'flex' : 'none';
        
        // Left page
        const leftPageIndex = i * 2;
        if (leftPageIndex < imageData.length) {
            const leftPage = createPage(imageData[leftPageIndex]);
            spreadContainer.appendChild(leftPage);
        }
        
        // Right page
        const rightPageIndex = i * 2 + 1;
        if (rightPageIndex < imageData.length) {
            const rightPage = createPage(imageData[rightPageIndex]);
            spreadContainer.appendChild(rightPage);
        } else {
            const emptyPage = document.createElement('div');
            emptyPage.className = 'page';
            spreadContainer.appendChild(emptyPage);
        }
        
        gallery.appendChild(spreadContainer);
    }
}

function createPage(imageInfo) {
    const page = document.createElement('div');
    page.className = 'page';
    
    const img = document.createElement('img');
    img.src = imageInfo.src;
    img.alt = imageInfo.caption;
    
    const caption = document.createElement('div');
    caption.className = 'caption';
    caption.textContent = imageInfo.caption;
    
    page.appendChild(img);
    page.appendChild(caption);
    
    return page;
}

function nextSpread() {
    if (isAnimating) return;
    
    const spreads = gallery.querySelectorAll('.spread-container');
    if (currentSpreadIndex >= spreads.length - 1) return;
    
    isAnimating = true;
    
    const currentSpread = spreads[currentSpreadIndex];
    currentSpread.classList.add('turning');
    
    setTimeout(() => {
        currentSpread.style.display = 'none';
        currentSpread.classList.remove('turning');
        
        currentSpreadIndex++;
        spreads[currentSpreadIndex].style.display = 'flex';
        isAnimating = false;
    }, 1000);
}

function prevSpread() {
    if (isAnimating) return;
    if (currentSpreadIndex <= 0) return;
    
    isAnimating = true;
    
    const spreads = gallery.querySelectorAll('.spread-container');
    const currentSpread = spreads[currentSpreadIndex];
    currentSpread.style.display = 'none';
    
    currentSpreadIndex--;
    const prevSpread = spreads[currentSpreadIndex];
    
    prevSpread.style.display = 'flex';
    prevSpread.classList.add('turning-back');
    
    setTimeout(() => {
        prevSpread.classList.remove('turning-back');
        isAnimating = false;
    }, 1000);
}

function startAutoTurn() {
    if (!autoTurnInterval) {
        autoTurnInterval = setInterval(() => {
            const spreads = gallery.querySelectorAll('.spread-container');
            if (currentSpreadIndex >= spreads.length - 1) {
                // Reset to first page when reaching the end
                currentSpreadIndex = -1;
                spreads.forEach(spread => spread.style.display = 'none');
                spreads[0].style.display = 'flex';
            }
            nextSpread();
        }, AUTO_TURN_DELAY);
    }
}

function stopAutoTurn() {
    if (autoTurnInterval) {
        clearInterval(autoTurnInterval);
        autoTurnInterval = null;
    }
}

initGallery();

document.getElementById('nextBtn').addEventListener('click', () => {
    stopAutoTurn();
    nextSpread();
});
document.getElementById('prevBtn').addEventListener('click', () => {
    stopAutoTurn();
    prevSpread();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') {
        stopAutoTurn();
        nextSpread();
    } else if (e.key === 'ArrowLeft') {
        stopAutoTurn();
        prevSpread();
    } else if (e.key === 'Space') {
        // Toggle auto-turn on space key
        if (autoTurnInterval) {
            stopAutoTurn();
        } else {
            startAutoTurn();
        }
    }
});

// Start auto-turn when the page loads
startAutoTurn();

// Optional: Pause auto-turn when user hovers over the gallery
gallery.addEventListener('mouseenter', stopAutoTurn);
gallery.addEventListener('mouseleave', startAutoTurn);
