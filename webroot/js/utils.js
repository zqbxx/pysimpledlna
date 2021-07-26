function debounce(func, wait, immediate) {
    var timeout;
    return function() {
        var context = this, args = arguments;
        var later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

function padLeft(value, length) {
  return (value.toString().length < length) ? padLeft("0"+value, length):value;
}

function formatTime(timeInSecond) {
    if (timeInSecond < 0) {
        return '-' + formatTime(-timeInSecond)
    }
    let m = Math.floor(timeInSecond / 60);
    let s = timeInSecond % 60;
    let h = Math.floor(m / 60);
    m = m % 60;
    return padLeft(h, 2) + ":" + padLeft(m, 2) + ":" + padLeft(s, 2);
}

function hasClass(element, className) {
    for ( let i = 0 ; i < element.classList.length; i++ ) {
        if (className == element.classList[i]) {
            return true;
        }
    }
    return false;
}

