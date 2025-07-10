function hidePost(postId, toggle) {
    if (confirm("Вы уверены ?")) {
        fetch("{{ url_for('blog.toggle_hide_post') }}", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: "post_id=" + encodeURIComponent(postId) + "&toggle=" + encodeURIComponent(toggle),
        }).then(response => {
            if (response.redirected) {
                window.location.href = response.url; // перенаправление после обработки
            } else {
                window.location.reload(); // или просто обновляем страницу
            }
        });
    }
}