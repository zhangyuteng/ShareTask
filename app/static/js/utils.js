const MyUtils = {};
MyUtils.install = function (Vue, options) {
    Vue.prototype.$post = function (url, data, callback, auto_redirect = true) {
        Vue.http.post(url, data)
            .then(function (response) {
                const res = response.data;
                if (res.status === 'success'){
                    if (res.message !== ''){
                        ELEMENT.Notification.success(res.message);
                    }
                    callback(res);
                }else{
                    if (res.message !== ''){
                        ELEMENT.Notification.error(res.message);
                    }
                }
                if (res.redirect !== '' && auto_redirect){
                    setTimeout(function () {
                        location.href = res.redirect
                    }, 2000)
                }
            }, function (response) {
                ELEMENT.Notification.error('网络错误，请刷新后重试');
                console.log(response);
            });
    };
    Vue.prototype.$loginpost = function (url, data, callback, errorCallback, auto_redirect = true) {
        Vue.http.post(url, data)
            .then(function (response) {
                callback(response)
                const user = response.data.response.user;
                localStorage.setItem('authentication_token', user.authentication_token);
                localStorage.setItem('uid', user.id);
                ELEMENT.Notification.success('Login Sucess');
                setTimeout(function () {
                    location.href = '/'
                }, 1200)
            }, function (response) {
                errorCallback(response);
                const errors = response.data.response.errors;
                if(errors){
                    let message = '';
                    for(let v in errors){
                        message += errors[v];
                    }
                    ELEMENT.Notification.error(message);
                }else{
                    ELEMENT.Notification.error('网络错误，请刷新后重试');
                }

            });
    };
    Vue.prototype.$get = function (url, callback, auto_redirect = true) {
        Vue.http.get(url)
            .then(function (response) {
                const res = response.data;
                if (res.status === 'success'){
                    if (res.message !== ''){
                        ELEMENT.Notification.success(res.message);
                    }
                    callback(res);
                }else{
                    if (res.message !== ''){
                        ELEMENT.Notification.error(res.message);
                    }
                }
                if (res.redirect !== '' && auto_redirect){
                    setTimeout(function () {
                        location.href = res.redirect
                    }, 2000)
                }
            }, function (response) {
                ELEMENT.Notification.error('网络错误，请刷新后重试');
                console.log(response);
            });
    }
};
Vue.use(MyUtils);