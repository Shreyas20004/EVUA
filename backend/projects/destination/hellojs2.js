function fetchData(callback) {
    setTimeout(() => {
        const data = { id: 1, message: "Hello from server" };
        callback(null, data);
    }, 1000);
}

fetchData((error, result) => {
    if (error) {
        console.log("Error:", error);
    } else {
        console.log("Data received:", result);
    }
});
