// Инициализация Telegram Web App
const tg = window.Telegram.WebApp;
tg.expand(); // Развернуть на весь экран

// Получаем данные пользователя
const user = tg.initDataUnsafe.user;
const userId = user.id;
const firstName = user.first_name;

// Регистрируем пользователя
fetch('/api/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        user_id: userId,
        username: user.username,
        first_name: firstName
    })
});

// Получаем ID чека из URL
const urlParams = new URLSearchParams(window.location.search);
const checkId = urlParams.get('check_id');

let checkData = null;

// Загружаем чек
async function loadCheck() {
    const response = await fetch(`/api/checks/${checkId}`);
    checkData = await response.json();
    renderItems();
}

// Рендерим список товаров
function renderItems() {
    const itemsList = document.getElementById('items-list');
    itemsList.innerHTML = '';
    
    checkData.items.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'item';
        
        const isOwner = item.owners.includes(userId);
        
        itemDiv.innerHTML = `
            <div class="item-header">
                <span class="item-name">${item.name}</span>
                <span class="item-price">${item.price} ₽</span>
            </div>
            <div class="owners">
                <button class="owner-btn ${isOwner ? 'active' : ''}" data-item-id="${item.id}">
                    ${isOwner ? '✓ Мое' : 'Мое'}
                </button>
            </div>
        `;
        
        itemsList.appendChild(itemDiv);
    });
    
    // Добавляем обработчики кликов
    document.querySelectorAll('.owner-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const itemId = btn.dataset.itemId;
            
            // Отправляем запрос на сервер
            await fetch(`/api/items/${itemId}/owners`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId })
            });
            
            // Перезагружаем данные
            await loadCheck();
            
            // Haptic feedback
            tg.HapticFeedback.impactOccurred('light');
        });
    });
}

// Кнопка "Подвести итог"
document.getElementById('finish-btn').addEventListener('click', async () => {
    if (!confirm('Завершить распределение?')) return;
    
    const response = await fetch(`/api/checks/${checkId}/finish`, {
        method: 'POST'
    });
    
    const result = await response.json();
    
    // Показываем результат
    let message = '🧾 Итоги:\n\n';
    result.debts.forEach(debt => {
        message += `👤 ${debt.name}: ${debt.debt} ₽\n`;
    });
    
    alert(message);
    
    // Закрываем Mini App
    tg.close();
});

// Загружаем данные при старте
loadCheck();