let currentImage = 0;
let imageIds = ['carousel1', 'carousel3', 'carousel4', 'carousel5', 'carousel6'];

function showNextImage() {
    if (imageIds.length === 0) return; // 如果没有图片，直接返回

    document.getElementById(imageIds[currentImage]).style.display = 'none';
    currentImage = (currentImage + 1) % imageIds.length;
    document.getElementById(imageIds[currentImage]).style.display = 'block';
}

setInterval(showNextImage, 3000); // 切换时间间隔为3秒

document.addEventListener("DOMContentLoaded", function () {
    document.getElementById('carousel1').addEventListener('click', function () {
        window.location.href = '/recite';
    });

    // 初始化显示第一张图片
    if (imageIds.length > 0) {
        document.getElementById(imageIds[0]).style.display = 'block';
    }

    // 监听图片删除事件
    const carousel = document.getElementById('carousel');
    if (!carousel) {
        console.error('Carousel element not found');
        return;
    }

    const observer = new MutationObserver(function (mutationsList) {
        mutationsList.forEach(function (mutation) {
            if (mutation.type === 'childList' && mutation.removedNodes.length > 0) {
                const removedNodesArray = Array.from(mutation.removedNodes);
                removedNodesArray.forEach(removedNode => {
                    if (removedNode.nodeType === Node.ELEMENT_NODE && removedNode.tagName === 'IMG') {
                        const index = imageIds.indexOf(removedNode.id);
                        if (index > -1) {
                            imageIds.splice(index, 1); // 从列表中移除被删除的图片ID

                            // 调整 currentImage
                            if (index === currentImage) {
                                currentImage = currentImage % imageIds.length;
                            } else if (index < currentImage) {
                                currentImage = (currentImage - 1 + imageIds.length) % imageIds.length;
                            }

                            // 确保只有 currentImage 指向的图片显示
                            if (imageIds.length > 0) {
                                imageIds.forEach((id, idx) => {
                                    const img = document.getElementById(id);
                                    if (img) {
                                        img.style.display = idx === currentImage ? 'block' : 'none';
                                    }
                                });
                            } else {
                                currentImage = 0; // 如果没有图片了，重置 currentImage
                            }
                        }
                    }
                });
            }
        });
    });

    observer.observe(carousel, { childList: true });

    // 检查图片路径是否存在，如果不存在则删除对应的 ID
    function checkImagesExistence() {
        imageIds = imageIds.filter(id => {
            const img = document.getElementById(id);
            return img && img.complete && img.naturalHeight !== 0;
        });

        // 调整 currentImage
        if (currentImage >= imageIds.length) {
            currentImage = 0;
        }

        // 确保只有 currentImage 指向的图片显示
        if (imageIds.length > 0) {
            imageIds.forEach((id, idx) => {
                const img = document.getElementById(id);
                if (img) {
                    img.style.display = idx === currentImage ? 'block' : 'none';
                }
            });
        }
    }

    // 在文档加载完毕后检查图片存在性
    checkImagesExistence();
});