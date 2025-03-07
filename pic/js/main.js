/**
 * 视频应用原型 - 主要JavaScript文件
 * 提供基本的交互功能
 */

// 等待DOM加载完成
document.addEventListener('DOMContentLoaded', function() {
  // 更新状态栏时间
  updateStatusBarTime();
  setInterval(updateStatusBarTime, 60000); // 每分钟更新一次
  
  // 初始化底部导航栏点击事件
  initTabBar();
  
  // 初始化搜索功能（如果在搜索页面）
  initSearch();
  
  // 初始化播放器控制（如果在播放页面）
  initPlayer();
  
  // 添加其他页面特定的初始化
  initPageSpecific();
});

/**
 * 更新状态栏时间
 */
function updateStatusBarTime() {
  const timeElements = document.querySelectorAll('.status-bar-time');
  if (timeElements.length > 0) {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const timeString = `${hours}:${minutes}`;
    
    timeElements.forEach(el => {
      el.textContent = timeString;
    });
  }
}

/**
 * 初始化底部导航栏
 */
function initTabBar() {
  const tabItems = document.querySelectorAll('.tab-item');
  
  tabItems.forEach(tab => {
    tab.addEventListener('click', function() {
      // 在实际应用中，这里会导航到相应页面
      // 在原型中，我们只模拟点击效果
      
      // 移除所有active类
      tabItems.forEach(t => t.classList.remove('active'));
      
      // 添加active类到当前点击的项
      this.classList.add('active');
      
      // 获取当前标签名称（用于模拟导航）
      const tabName = this.querySelector('span').textContent;
      console.log(`导航到: ${tabName}`);
      
      // 如果在同一页面内，可以模拟页面切换
      simulateNavigation(tabName);
    });
  });
}

/**
 * 模拟导航（仅用于原型演示）
 */
function simulateNavigation(tabName) {
  // 这个函数在实际应用中会导航到不同页面
  // 在原型中，我们只在控制台显示信息
  
  // 映射标签名称到页面URL（如果在同一个原型中需要实际导航）
  const pageMap = {
    '首页': 'home.html',
    '搜索': 'search.html',
    '分类': 'categories.html',
    '我的': 'mylist.html',
    '账户': 'profile.html'
  };
  
  // 获取当前页面路径
  const currentPath = window.location.pathname;
  const currentPage = currentPath.substring(currentPath.lastIndexOf('/') + 1);
  
  // 如果点击的不是当前页面，且我们不在index.html中
  if (pageMap[tabName] && pageMap[tabName] !== currentPage && currentPage !== 'index.html') {
    // 在实际应用中，这里会使用window.location.href进行导航
    console.log(`将导航到: ${pageMap[tabName]}`);
    
    // 如果需要在原型中实际导航，取消下面这行的注释
    // window.location.href = pageMap[tabName];
  }
}

/**
 * 初始化搜索功能
 */
function initSearch() {
  const searchInput = document.querySelector('.search-input');
  if (searchInput) {
    searchInput.addEventListener('focus', function() {
      console.log('搜索框获得焦点');
    });
    
    searchInput.addEventListener('input', function() {
      console.log(`搜索: ${this.value}`);
      // 在实际应用中，这里会触发搜索建议
    });
  }
}

/**
 * 初始化播放器控制
 */
function initPlayer() {
  const playButton = document.querySelector('.fa-pause');
  if (playButton) {
    playButton.addEventListener('click', function() {
      // 切换播放/暂停图标
      if (this.classList.contains('fa-pause')) {
        this.classList.remove('fa-pause');
        this.classList.add('fa-play');
        console.log('视频已暂停');
      } else {
        this.classList.remove('fa-play');
        this.classList.add('fa-pause');
        console.log('视频已播放');
      }
    });
    
    // 初始化进度条交互
    const progressBar = document.querySelector('.bg-red-600');
    const progressContainer = document.querySelector('.bg-gray-600');
    
    if (progressContainer) {
      progressContainer.addEventListener('click', function(e) {
        // 计算点击位置相对于进度条的百分比
        const rect = this.getBoundingClientRect();
        const position = (e.clientX - rect.left) / rect.width;
        
        // 更新进度条位置
        if (progressBar) {
          progressBar.style.width = `${position * 100}%`;
          
          // 更新进度球位置
          const progressBall = document.querySelector('.rounded-full.-mt-1');
          if (progressBall) {
            progressBall.style.left = `${position * 100}%`;
          }
          
          console.log(`视频进度: ${Math.round(position * 100)}%`);
        }
      });
    }
  }
}

/**
 * 初始化页面特定功能
 */
function initPageSpecific() {
  // 获取当前页面路径
  const currentPath = window.location.pathname;
  const currentPage = currentPath.substring(currentPath.lastIndexOf('/') + 1);
  
  // 根据当前页面添加特定功能
  switch (currentPage) {
    case 'details.html':
      // 详情页特定功能
      initDetailsPage();
      break;
    case 'profile.html':
      // 个人资料页特定功能
      initProfilePage();
      break;
    case 'mylist.html':
      // 我的列表页特定功能
      initMyListPage();
      break;
  }
}

/**
 * 初始化详情页特定功能
 */
function initDetailsPage() {
  // 添加收藏按钮功能
  const addButton = document.querySelector('.btn-secondary');
  if (addButton) {
    addButton.addEventListener('click', function() {
      console.log('已添加到我的列表');
      // 在实际应用中，这里会显示一个确认消息
      showToast('已添加到我的列表');
    });
  }
}

/**
 * 初始化个人资料页特定功能
 */
function initProfilePage() {
  // 深色模式切换
  const toggleCheckbox = document.getElementById('toggle');
  if (toggleCheckbox) {
    toggleCheckbox.addEventListener('change', function() {
      console.log(`深色模式: ${this.checked ? '开启' : '关闭'}`);
    });
  }
}

/**
 * 初始化我的列表页特定功能
 */
function initMyListPage() {
  // 删除按钮功能
  const deleteButtons = document.querySelectorAll('.fa-trash');
  deleteButtons.forEach(button => {
    button.addEventListener('click', function() {
      // 获取最近的列表项
      const listItem = this.closest('.flex.bg-gray-800');
      if (listItem) {
        console.log('从列表中移除项目');
        // 在实际应用中，这里会显示一个确认对话框
        // 在原型中，我们只添加一个淡出效果
        listItem.style.opacity = '0.5';
      }
    });
  });
}

/**
 * 显示提示消息
 */
function showToast(message) {
  // 创建toast元素
  const toast = document.createElement('div');
  toast.className = 'fixed bottom-20 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white px-4 py-2 rounded-md';
  toast.textContent = message;
  
  // 添加到页面
  document.body.appendChild(toast);
  
  // 2秒后移除
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.5s';
    
    setTimeout(() => {
      document.body.removeChild(toast);
    }, 500);
  }, 2000);
}
