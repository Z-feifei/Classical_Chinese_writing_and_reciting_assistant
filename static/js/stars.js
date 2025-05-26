document.addEventListener('DOMContentLoaded', () => {
    const ratings = document.querySelectorAll('.rating-item');

    ratings.forEach(ratingItem => {
        const stars = ratingItem.querySelectorAll('.stars label');
        stars.forEach(star => {
            star.addEventListener('mouseover', () => {
                const allStars = star.parentNode.querySelectorAll('label');
                allStars.forEach(s => s.style.color = '#ccc');
                star.style.color = '#fd4';
                let prevStar = star.previousElementSibling;
                while (prevStar) {
                    prevStar.style.color = '#fd4';
                    prevStar = prevStar.previousElementSibling;
                }
            });

            star.addEventListener('click', (e) => {
                const allStars = star.parentNode.querySelectorAll('label');
                allStars.forEach(s => s.style.color = '#ccc'); // 首先重置颜色
                star.style.color = '#fd4'; // 设置当前星星为黄色
                let prevStar = star.previousElementSibling;
                while (prevStar) {
                    prevStar.style.color = '#fd4'; // 设置左侧星星为黄色
                    prevStar = prevStar.previousElementSibling;
                }
            });
        });

        ratingItem.addEventListener('mouseout', () => {
            const checkedStar = ratingItem.querySelector('.stars input:checked');
            if (checkedStar) {
                const allStars = checkedStar.parentNode.querySelectorAll('label');
                allStars.forEach(s => s.style.color = '#ccc'); // 首先重置颜色
                const checkedLabel = ratingItem.querySelector(`label[for="${checkedStar.id}"]`);
                checkedLabel.style.color = '#fd4'; // 设置当前星星为黄色
                let prevStar = checkedLabel.previousElementSibling;
                while (prevStar) {
                    prevStar.style.color = '#fd4'; // 设置左侧星星为黄色
                    prevStar = prevStar.previousElementSibling;
                }
            } else {
                const allStars = ratingItem.querySelectorAll('.stars label');
                allStars.forEach(s => s.style.color = '#ccc'); // 重置所有星星颜色为灰色
            }
        });
    });
});
