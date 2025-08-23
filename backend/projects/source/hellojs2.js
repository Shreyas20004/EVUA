function fetchData(callback) {
    setTimeout(function() {
        var data = { id: 1, message: "Hello from server" };
        callback(null, data);
    }, 1000);
}

fetchData(function(error, result) {
    if (error) {
        console.log("Error:", error);
    } else {
        console.log("Data received:", result);
    }
});
