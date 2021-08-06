mui.init();
mui.ready(function() {

    //let userPicker = new mui.PopPicker();
    
    device_key = '{device_key}'
    
    let global = {
        currentSelectedIndex: 0,
        currentStatus: 'Play',
        currentPosition: 0,
        playingFileName: '',
        playingFilePath: '',
        videoDuration: 0,
        apiUrl: '../api/' + device_key,
        isSeeking: false,
        currentPlaylistName: '',
        playlistFileNameList: [],
        isOccupied: undefined,
        chimee: undefined,
        isLocal: false,
    };

    let playListPicker = new mui.PopPicker();

    let mask = mui.createMask();

    // 圆形进度条
    circleProgress = new CircleProgress('.circle-progress-content')
        .attr('max', 100)
        .attr('value', 0)
        .attr('animationDuration', 0)
        .attr('textFormat', function(value, max) {
            if(global.currentStatus == 'Play') {
                return '&#xf04c';
			} else if (global.currentStatus == 'Pause' || global.currentStatus == 'Stop') {
				return '&#xf04b';
			}
		});

	mui('#circle-progress-wrapper').on('click', '.circle-progress-content', function(){
		if(global.currentStatus == 'Play') {
			global.currentStatus = 'Pause';
			mui.getJSON(global.apiUrl,{command:'pause', r: '' +new Date().getTime()},function(data){});
		} else if (global.currentStatus == 'Pause') {
		    global.currentStatus = 'Play';
		    mui.getJSON(global.apiUrl,{command:'play', r: '' +new Date().getTime()},function(data){});
		} else if (global.currentStatus = 'Stop') {
            ele = document.querySelector('#video-file-list button.mui-btn-danger')
            if (ele != null) {
                if (hasClass(ele, 'fa-play')) {
                    mui.getJSON(global.apiUrl,
                        {
                            command:'index',
                            r: '' +new Date().getTime(),
                            index: ele.getAttribute('videoIndex'),
                            name: ele.getAttribute('videoName')
                        },
                        function(data){

                        }
                    );
                }

            }
        }
	})

    // 视频选择
	/*var showUserPickerButton = document.getElementById('select-video');
	showUserPickerButton.addEventListener('tap', function(event) {
		userPicker.pickers[0].setSelectedIndex(currentSelectedIndex, 1000)
		userPicker.show(function(items) {
		    userSelectIndex = parseInt(items[0].value)
            mui.getJSON(api_url,{command:'index', index: userSelectIndex, r: '' +new Date().getTime()},function(data){
                    console.log(data);
                    showUserPickerButton.innerText = items[0].text;
                }
            );

			//返回 false 可以阻止选择框的关闭
			//return false;
		});
	}, false);*/

    //屏幕常亮
    var lightVideo = document.getElementById('light');
    var lightHandle = document.getElementById('light-handle');
    var noSleep = new NoSleep();

	lightHandle.addEventListener('toggle', function(event) {
	    if (event.detail.isActive) {
	        noSleep.enable()
	    } else {
	        noSleep.disable();
	    }
	});


    //进度跳转
    let offset = 0
    function updateSeekInfo(t) {
        formattedTime = formatTime(t);
        if (!formattedTime.startsWith('-') && t != 0) {
            formattedTime = '+' + formattedTime;
        }
        document.getElementById('timeOffsetInfo').innerHTML =
          (t == 0 ? '' : formattedTime + '/')
        +formatTime(global.currentPosition)
        + (t == 0 ? '' : '(' + formatTime(global.currentPosition + t)  + ')');
    }
    updateSeekInfo(0);
    let seekBtnFunc = function() {
    	if (global.isLocal) {
	        return;
	    }
        global.isSeeking = true
        offset += parseInt(this.getAttribute('timeOffset'));
        if ((offset < 0) && (global.currentPosition + offset < 0) ) {
            offset = -global.currentPosition;
        } else if (offset + global.currentPosition > global.videoDuration) {
            offset = global.videoDuration - global.currentPosition;
        }
		updateSeekInfo(offset);
	};
	let seekBtnEndFunc = debounce(function() {
	    if (global.isLocal) {
	        return;
	    }
	    mui.getJSON(global.apiUrl,{command:'seek', pos:offset, r: '' +new Date().getTime()},function(data){

	    });
	    offset = 0;
	    updateSeekInfo(0);
	    setTimeout(function(){
	        global.isSeeking = false;
	    }, 1000)
	}, 1000);

	let offsetBtns = document.querySelectorAll('.timeSeekButton')
	for (let ob of offsetBtns) {
		ob.addEventListener('click', seekBtnFunc)
		ob.addEventListener('click', seekBtnEndFunc)
	}

    let startPos = 0
    let progressBar = document.getElementById('progressBar');
    let rangeSeekStartFunc = function(){
        startPos = global.currentPosition;
        global.isSeeking = true
    }

	let rangeSeekFunc = function() {
	    offset = progressBar.value - startPos
	    updateSeekInfo(offset);
	};
	let rangeSeekEndFunc =function() {
	    mui.getJSON(global.apiUrl,{command:'seek', pos:offset, r: '' +new Date().getTime()},function(data){

	    });
	    offset = 0;
	    startPos = 0;
	    updateSeekInfo(0);
	    setTimeout(function(){
	        global.isSeeking = false;

	    }, 1000)

	};

	progressBar.min = 0;
	progressBar.max = global.videoDuration;
	progressBar.addEventListener('mousedown', rangeSeekStartFunc);
	progressBar.addEventListener('touchstart', rangeSeekStartFunc);
	progressBar.addEventListener('input', rangeSeekFunc);
	progressBar.addEventListener('mouseup', rangeSeekEndFunc);
	progressBar.addEventListener('touchend', rangeSeekEndFunc);

    //数据更新
    function updateData() {
        if (global.isLocal)
            return
        if (!global.isSeeking) {
            mui.getJSON(global.apiUrl,{command:'status', r: '' +new Date().getTime()},function(data){

                    if (!global.isSeeking) {

                        playlist_changed = global.currentPlaylistName != data.current_playlist_name;
                        current_video_changed = global.currentSelectedIndex != data.index;
                        video_position_changed = global.currentPosition !=  data.position;
                        player_status_changed = global.currentStatus != data.current_status
                        occupied_status_changed = global.isOccupied != data.is_occupied

                        // 深拷贝
                        let oldGlobal = Object.assign({}, global);
                        oldGlobal.playlistFileNameList = global.playlistFileNameList.slice();

                        // 当前播放的视频状态
                        global.currentPosition = data.position;
                        global.videoDuration = data.duration;
                        global.currentStatus = data.current_status;
                        global.currentSelectedIndex = data.index_in_playlist;
                        global.isOccupied = data.is_occupied

                        // 当前播放的播放列表状态
                        global.playingFilePath = data.playing_file_path;
                        global.playingFileName = data.playing_file_name
                        global.playlistFileNameList = data.file_name_list
                        global.currentPlaylistName = data.current_playlist_name;

                        if (player_status_changed) {
                            if (global.currentStatus == 'Stop') {
                                document.getElementById('stopVideo').disabled = true;
                            } else {
                                document.getElementById('stopVideo').disabled = false;
                            }
                        }

                        if (occupied_status_changed || player_status_changed) {
                            let txtStatus = document.getElementById('playerStatus')
                            if(global.isOccupied)
                                txtStatus.innerHTML = '投屏被占用';
                            else if (global.currentStatus == 'Stop')
                                txtStatus.innerHTML = '已停止投屏';
                            else if (global.currentStatus == 'Pause')
                                txtStatus.innerHTML = '投屏已暂停';
                            else if (global.currentStatus == 'Play')
                                txtStatus.innerHTML = '正在播放'
                        }
                        document.getElementById('currentFileName').innerHTML = global.playingFileName;
                        //document.getElementById('current_file_time').innerHTML = data.position + '/' + data.duration;
                        //mui('#video-progress-bar').progressbar().setProgress(Math.round(data.position/data.duration*100));
                        circleProgress.attr({ value: data.position, });

                        if (playlist_changed) {
                            document.getElementById('playlist-name').innerText = global.currentPlaylistName;
                            createPlaylistVideos(data.file_name_list, data.index);
                        }

                        if (current_video_changed){
                            circleProgress.attr({ max: data.duration, });
                            progressBar.max = global.videoDuration;
                        }

                        if (video_position_changed) {
                            progressBar.value = global.currentPosition;
                            timeInfoText = formatTime(global.currentPosition) + '/' + formatTime(global.videoDuration);
                            document.getElementById('timeInfo').innerText = timeInfoText;
                            updateSeekInfo(0);
                        }

                        if (current_video_changed || playlist_changed) {
                            updatePlaylistVideoStatus(data)
                        }

                    }

                }
            );
        }

    }

    //获取播放列表
    function getAllPlaylist() {
        mui.getJSON(global.apiUrl,{command:'getAllPlaylist', r: '' +new Date().getTime()}, function(data){
            console.log(data);
            let pickerData = new Array();
            for(let i = 0; i < data.length; i++) {
                pickerData[i] = {
                    value: data[i],
                    text: data[i]
                }
            }
            playListPicker.setData(pickerData)
        });
    }

    mui('#morePlaylist')[0].addEventListener('tap', function(){
		playListPicker.pickers[0].setSelectedValue(global.currentPlaylistName, 1000)
		playListPicker.show(function(items) {
		    selectedPlaylistName = items[0].value
		    if (selectedPlaylistName == global.currentPlaylistName) {
		        return
		    }
		    mask.show();
		    mui.getJSON(global.apiUrl,{command:'switchPlayList', o: '', n: selectedPlaylistName, r: '' +new Date().getTime()},function(data){
		            global.currentPlaylistName = selectedPlaylistName;
		            document.getElementById('playlist-name').innerText = global.currentPlaylistName;
		            createPlaylistVideos(data.file_name_list, data.index);
                    mui.later(function(){
						mask.close();
					}, 300);
                }
            );
		});
    });

    document.getElementById('stopVideo').addEventListener('click', function() {
        mui.getJSON(global.apiUrl,{command:'stop', r: '' +new Date().getTime()},function(data){});
        this.disabled = true;
    });

    document.getElementById('playLocal').addEventListener('click', function() {

        function updateButton(enable) {
            document.getElementById('stopVideo').disabled = enable;
            document.getElementById('progressBar').disabled = enable;
            document.getElementById('morePlaylist').disabled = enable;

            [].forEach.call(document.querySelectorAll('.timeSeekButton'), function(btn) {
              btn.disabled = enable;
            });
            [].forEach.call(document.querySelectorAll('#video-file-list > li > button'), function(btn) {
              btn.disabled = enable;
            });
        }

        thisElement = this;

        if (hasClass(this, 'fa-arrow-circle-left')) {
            mask.show();
            global.isLocal = false;
            let offset = parseInt(global.chimee.currentTime - global.currentPosition);
            global.chimee.destroy();
            mui.getJSON(global.apiUrl,{command:'play', r: '' +new Date().getTime()},function(data){
                thisElement.classList.add('fa-play-circle-o');
                thisElement.classList.remove('fa-arrow-circle-left');
                thisElement.innerText = '本机播放';
                document.getElementById('circleProgress').style.display = '';
                document.getElementById('videoPlayer').style.display = 'none';
                updateButton(false);
                let isFirst = true;
                let timer = setInterval(function(){
                    if (global.currentStatus == 'Play') {
                        clearInterval(timer);
                        mui.getJSON(global.apiUrl,{command:'seek', pos:offset, r: '' +new Date().getTime()},function(data){
                            mui.later(function(){
                                mask.close();
                            }, 100);
                        });
                    } else {
                        if (isFirst) {
                            // 手机端状态可能尚未更新，第一次进入跳过
                            isFirst = false;
                        } else {
                            //重新发送播放指令，有时候第一次发送无效
                            mui.getJSON(global.apiUrl,{command:'play', r: '' +new Date().getTime()},function(data){});
                        }

                    }
                }, 500);
            });
            mui.getJSON(global.apiUrl,{command:'seek', pos:offset, r: '' +new Date().getTime()},function(data){
                mui.getJSON(global.apiUrl,{command:'play', r: '' +new Date().getTime()},function(data){

                });
            });
        } else if (hasClass(this, 'fa-play-circle-o')) {
            mask.show();
            document.getElementById('circleProgress').style.display = 'none';
            document.getElementById('videoPlayer').style.display = '';
            global.isLocal = true;
            global.chimee = new ChimeeMobilePlayer({  wrapper: '#videoPlayer', controls: true, autoplay: true,})
            flag = -1;
            global.chimee.on('timeupdate', function(){
                if (flag == -1 && global.chimee.currentTime > 0.3) {
                    flag = 1;
                    global.chimee.currentTime = global.currentPosition;
                }
			});
			mui.getJSON(global.apiUrl,{command:'pause', r: '' +new Date().getTime()},function(data){
                global.chimee.load(global.apiUrl + '?command=playAtApp');
                thisElement.classList.remove('fa-play-circle-o');
                thisElement.classList.add('fa-arrow-circle-left');
                thisElement.innerText = '返回投屏';
                updateButton(true)
                mui.later(function(){
					mask.close();
				}, 300);
			});

        }
    });

    function createPlaylistVideos(file_name_list, index) {
        videoFileList = document.getElementById('video-file-list');
		videoFileList.innerHTML = ''
        for (let i = 0; i < file_name_list.length; i++) {
            let li = document.createElement('li');
            li.className = 'mui-table-view-cell';
            let spanName = document.createElement('span');
            spanName.className = 'playlist-video-item-name';
            spanName.innerHTML = file_name_list[i];
            let btn = document.createElement('button');
            btn.setAttribute('videoName', file_name_list[i])

            if (index == i){
                btn.className = 'mui-btn fa';
            } else {
                btn.className = 'mui-btn fa';
            }

            btn.setAttribute('videoIndex', "" + i)

            li.appendChild(spanName)
            li.appendChild(btn)
            btn.addEventListener('tap', function() {
                currentIndex = -1;
                if (hasClass(this, 'fa-play')) {
                    currentIndex = this.getAttribute('videoIndex');
                }
                mui.getJSON(
                        global.apiUrl,
                        {
                            command:'index',
                            index: currentIndex,
                            name: this.getAttribute('videoName'),
                            r: '' + new Date().getTime(),
                        },
                        function(data){
                            updatePlaylistVideoStatus(data);
                        }
                 );
            })
            videoFileList.appendChild(li);
        }
        updatePlaylistVideoStatus({});
    }

    function updatePlaylistVideoStatus(data) {
        if (data.index)
            global.currentSelectedIndex = data.index
        if (data.current_status)
            global.currentStatus = data.current_status
        let btnArray = document.querySelectorAll('#video-file-list button');
        for (let j = 0 ; j < btnArray.length ; j++ ) {
            if ( j != global.currentSelectedIndex ) {
                btnArray[j].classList.remove('fa-stop');
                btnArray[j].classList.add('fa-play');
                btnArray[j].classList.remove('mui-btn-danger');
                btnArray[j].classList.add('mui-btn-primary');
            } else {
                if (global.currentStatus == 'Stop' || btnArray[j].getAttribute('videoName') != global.playingFileName) {
                    btnArray[j].classList.remove('fa-stop');
                    btnArray[j].classList.add('fa-play');
                } else {
                    btnArray[j].classList.remove('fa-play');
                    btnArray[j].classList.add('fa-stop');
                }
                btnArray[j].classList.remove('mui-btn-primary');
                btnArray[j].classList.add('mui-btn-danger');
            }
        }
    }


    updateData();
    getAllPlaylist();

    setInterval(updateData, 500)
});