mui.init();
mui.ready(function() {
    
    device_key = '{device_key}';
    
    let global = {
        apiUrl: '../api/' + device_key,
        isSeeking: false,
        chimee: undefined,
        isLocal: false,
        currentPlaylist: { name: '', index: -1, skipHead: 0, skipTail: 0, videoList: []},
        currentVideo: { path: '', name: '', position: -1, duration: -1, },
        dlnaPlayer: { occupied: false, status: "", },
        viewPlaylist: { name: '', index: -1, position: -1, duration: -1, videoList: [], },
    };

    let local = {
        currentPlaylist: { name: '', index: -1, skipHead: 0, skipTail: 0, videoList: []},
        currentVideo: {path: '', name: '', position: -1, duration: -1, }
    }

    let playListPicker = new mui.PopPicker();

    let mask = mui.createMask();

    // 圆形进度条
    circleProgress = new CircleProgress('.circle-progress-content')
        .attr('max', 100)
        .attr('value', 0)
        .attr('animationDuration', 0)
        .attr('textFormat', function(value, max) {
            if(global.dlnaPlayer.status == 'Play') {
                return '&#xf04c';
			} else if (global.dlnaPlayer.status == 'Pause' || global.dlnaPlayer.status == 'Stop') {
				return '&#xf04b';
			}
			return '&#xf04b';
		});

	mui('#circle-progress-wrapper').on('click', '.circle-progress-content', function(){
		if(global.dlnaPlayer.status == 'Play') {
			global.dlnaPlayer.status = 'Pause';
			pauseVideo(function(data){});
		} else if (global.dlnaPlayer.status == 'Pause') {
		    global.dlnaPlayer.status = 'Play';
		    resumeVideo(function(data){})
		} else if (global.dlnaPlayer.status = 'Stop') {
		    playVideo(global.currentPlaylist.index, global.currentVideo.name, global.currentPlaylist.name);
        }
	})

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

	var vConsoleToggle = document.getElementById('vConsoleToggle')
	vConsoleToggle.addEventListener('toggle', function(event) {
	    if (event.detail.isActive) {
	        vConsole.showSwitch()
	    } else {
	        vConsole.hideSwitch()
	    }
	});

    //进度跳转
    let offset = 0
    function updateSeekInfo(t, position) {
        formattedTime = formatTime(t);
        if (!formattedTime.startsWith('-') && t != 0) {
            formattedTime = '+' + formattedTime;
        }
        document.getElementById('timeOffsetInfo').innerHTML =
          (t == 0 ? '' : formattedTime + '/') + formatTime(position) + (t == 0 ? '' : '(' + formatTime(position + t)  + ')');
    }
    updateSeekInfo(0, global.currentVideo.position);
    let seekBtnFunc = function() {
	    position = -1;
	    duration = -1;
	    if (global.isLocal) {
	        position = local.currentVideo.position;
	        duration = local.currentVideo.duration;
	    } else {
	        position = global.currentVideo.position;
	        duration = global.currentVideo.duration;
	    }
        global.isSeeking = true
        offset += parseInt(this.getAttribute('timeOffset'));
        if ((offset < 0) && (position + offset < 0) ) {
            offset = -position;
        } else if (offset + position > duration) {
            offset = duration - position;
        }
		updateSeekInfo(offset, position);
	};
	let seekBtnEndFunc = debounce(function() {
	    if (global.isLocal) {
	        global.chimee.currentTime = offset + global.chimee.currentTime;
	        updateLocalData({
	            currentVideo: {
	                position: global.chimee.currentTime,
	            }
	        });
	    } else {
	        seek(offset, function(data){});
	        updateSeekInfo(0, global.currentVideo.position);
	    }
	    offset = 0;
	    if (global.isLocal) {
	        global.isSeeking = false;
	    } else {
	    	setTimeout(function(){
	            global.isSeeking = false;
            }, 1000);
	    }
	}, 1000);

	let offsetBtns = document.querySelectorAll('.timeSeekButton')
	for (let ob of offsetBtns) {
		ob.addEventListener('click', seekBtnFunc);
		ob.addEventListener('click', seekBtnEndFunc);
	}

    let startPos = 0;
    let endPos = 0;
    let progressBar = document.getElementById('progressBar');
    let rangeSeekStartFunc = function(){
        startPos = global.currentVideo.position;
        global.isSeeking = true;
    }

	let rangeSeekFunc = function() {
	    offset = Math.round(progressBar.value) - startPos;
	    endPos = Math.round(progressBar.value);
	    if (global.isLocal)
	        updateSeekInfo(offset, local.currentVideo.position);
	    else
	        updateSeekInfo(offset, global.currentVideo.position);
	};
	let rangeSeekEndFunc =function() {
	    if (global.isLocal) {
	        global.chimee.currentTime = endPos;
	        updateLocalData({
	            currentVideo: {
	                position: global.chimee.currentTime,
	            }
	        });
	    } else {
	        seek(offset, function(){})
	        updateSeekInfo(0, global.currentVideo.position);
	    }
	    offset = 0;
	    startPos = 0;
	    if (global.isLocal) {
	        global.isSeeking = false;
	    } else {
	    	setTimeout(function(){
	            global.isSeeking = false;
            }, 1000);
	    }

	};

	progressBar.min = 0;
	progressBar.max = global.currentVideo.duration;
	progressBar.addEventListener('mousedown', rangeSeekStartFunc);
	progressBar.addEventListener('touchstart', rangeSeekStartFunc);
	progressBar.addEventListener('input', rangeSeekFunc);
	progressBar.addEventListener('mouseup', rangeSeekEndFunc);
	progressBar.addEventListener('touchend', rangeSeekEndFunc);

    //数据更新
    function updateData() {

        if (!global.isSeeking) {
            mui.getJSON(global.apiUrl,{command:'status', r: '' +new Date().getTime()},function(data){

                    if (!global.isSeeking) {

                        playlist_changed = global.viewPlaylist.name != data.viewPlaylist.name;
                        current_video_changed =global.currentVideo.path != data.currentVideo.path;
                        video_position_changed = global.currentVideo.position != data.currentVideo.position;
                        player_status_changed = global.dlnaPlayer.status != data.dlnaPlayer.status;
                        occupied_status_changed = global.dlnaPlayer.occupied != data.dlnaPlayer.occupied;
                        video_duration_changed = global.currentVideo.duration != data.currentVideo.duration;

                        let old = {};
                        old.currentPlaylist = global.currentPlaylist;
                        old.currentVideo = global.currentVideo;
                        old.dlnaPlayer = global.dlnaPlayer;
                        old.viewPlaylist = global.viewPlaylist;

                        global.currentPlaylist = data.currentPlaylist;
                        global.currentVideo = data.currentVideo;
                        global.dlnaPlayer = data.dlnaPlayer;
                        global.viewPlaylist = data.viewPlaylist;

                        if (player_status_changed && !global.isLocal) {
                            if (data.dlnaPlayer.status == 'Stop') {
                                document.getElementById('stopVideo').disabled = true;
                            } else {
                                document.getElementById('stopVideo').disabled = false;
                            }
                        }

                        if (occupied_status_changed || player_status_changed) {
                            let txtStatus = document.getElementById('playerStatus')
                            if(data.dlnaPlayer.occupied)
                                txtStatus.innerHTML = '投屏被占用';
                            else if (data.dlnaPlayer.status == 'Stop')
                                txtStatus.innerHTML = '已停止投屏';
                            else if (data.dlnaPlayer.status == 'Pause')
                                txtStatus.innerHTML = '投屏已暂停';
                            else if (data.dlnaPlayer.status == 'Play')
                                txtStatus.innerHTML = '正在播放';
                        }
                        if (current_video_changed)
                            document.getElementById('currentFileName').innerHTML = data.currentVideo.name;

                        if (playlist_changed && !global.isLocal) {
                            document.getElementById('playlist-name').innerText = data.viewPlaylist.name;
                            createPlaylistVideos(data.viewPlaylist.videoList, data.viewPlaylist.index);
                        }

                        if (video_duration_changed || player_status_changed && !global.isLocal){
                            circleProgress.attr({ max: data.currentVideo.duration, });
                            progressBar.max = global.currentVideo.duration;
                        }

                        if (video_position_changed || player_status_changed && !global.isLocal) {
                            circleProgress.attr({ value: data.currentVideo.position, });
                            progressBar.value = data.currentVideo.position;
                            timeInfoText = formatTime(data.currentVideo.position) + '/' + formatTime(data.currentVideo.duration);
                            document.getElementById('timeInfo').innerText = timeInfoText;
                            updateSeekInfo(0, global.currentVideo.position);
                        }

                        if (current_video_changed || playlist_changed || player_status_changed && !global.isLocal) {
                            updatePlaylistVideoStatus(data);
                        }

                        if (current_video_changed || playlist_changed || player_status_changed || video_duration_changed || video_position_changed && !global.isLocal) {
                            updatePlaylistProgress();
                        }

                    }

                }
            );
        }

    }

    function updateLocalData(data) {
        if (document.getElementById('playerStatus').innerHTML != '本机播放')
            document.getElementById('playerStatus').innerHTML = '本机播放';
        if (data.currentVideo != undefined) {
            currentVideo = data.currentVideo
            if (currentVideo.name != undefined) {
                local.currentVideo.name = currentVideo.name;
                document.getElementById('currentFileName').innerHTML = local.currentVideo.name;
            }
            if (currentVideo.duration != undefined) {
                local.currentVideo.duration = currentVideo.duration;
                circleProgress.attr({ max: local.currentVideo.duration, });
                progressBar.max = local.currentVideo.duration;
            }
            if (currentVideo.position != undefined) {
                local.currentVideo.position = currentVideo.position;
                circleProgress.attr({ value: local.currentVideo.position, });
                if (!global.isSeeking) {
                    progressBar.value = local.currentVideo.position;
                    updateSeekInfo(0, currentVideo.position);
                    let playingRow = document.querySelector('#video-file-list > li.mui-table-view-cell.playing');
                    let playingVideoProgressText = playingRow.querySelector('.playlist-progress-text');
                    let playlistProgress = playingRow.querySelector('.playlist-progress');
                    if (currentVideo.duration > 0) {
                        percent = currentVideo.position / currentVideo.duration * 100;
                        playlistProgress.style.width = (percent > 1 ? percent.toFixed(0) : 1) + '%';
                        playingVideoProgressText.innerText = '(已播放:' + percent.toFixed(2) + '%)';
                    }
                }
                timeInfoText = formatTime(local.currentVideo.position) + '/' + formatTime(local.currentVideo.duration);
                document.getElementById('timeInfo').innerText = timeInfoText;
            }
        }
        if (data.currentPlaylist != undefined) {
            currentPlaylist = data.currentPlaylist
            if (currentPlaylist.name != undefined) {
                local.currentPlaylist.name = currentPlaylist.name;
            }
            if (currentPlaylist.index != undefined) {
                local.currentPlaylist.index = currentPlaylist.index;
                updatePlaylistVideoStatus({}, local);
            }
            if (currentPlaylist.name != undefined) {
                local.currentPlaylist.skipHead = currentPlaylist.skipHead;
            }
            if (currentPlaylist.name != undefined) {
                local.currentPlaylist.skipTail = currentPlaylist.skipTail;
            }
            if (currentPlaylist.name != undefined) {
                local.currentPlaylist.videoList = currentPlaylist.videoList;
            }
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
            playListPicker.setData(pickerData);
        });
    }

    mui('#morePlaylist')[0].addEventListener('tap', function(){
		playListPicker.pickers[0].setSelectedValue(global.viewPlaylist.name, 1000)
		playListPicker.show(function(items) {
		    selectedPlaylistName = items[0].value
		    if (selectedPlaylistName == global.viewPlaylist.name) {
		        return
		    }
		    mask.show();
		    mui.getJSON(global.apiUrl,{command:'switchPlayList', o: '', n: selectedPlaylistName, r: '' +new Date().getTime()},function(data){
		            global.viewPlaylist = data.viewPlaylist;
		            document.getElementById('playlist-name').innerText = global.viewPlaylist.name;
		            createPlaylistVideos(global.viewPlaylist.videoList, global.viewPlaylist.index);
                    mui.later(function(){
						mask.close();
					}, 300);
                }
            );
		});
    });

    document.getElementById('stopVideo').addEventListener('click', function() {
        stopVideo(function(data){});
        this.disabled = true;
    });

    document.getElementById('playLocal').addEventListener('click', function() {

        function updateButton(enable) {
            document.getElementById('stopVideo').disabled = enable;
            document.getElementById('morePlaylist').disabled = enable;

            /*[].forEach.call(document.querySelectorAll('#video-file-list > li > button'), function(btn) {
              btn.disabled = enable;
            });*/
        }

        thisElement = this;

        if (hasClass(this, 'fa-arrow-circle-left')) {
            mask.show();
            global.isLocal = false;
            let pos = parseInt(global.chimee.currentTime);
            let offset = parseInt(global.chimee.currentTime - global.currentPosition);
            global.chimee.destroy();
            mui.getJSON(global.apiUrl,{
                command:'backToDlna',
                pos: pos - 3,
                r: '' + new Date().getTime(),
                playlist: global.currentPlaylist.name,
                index: local.currentPlaylist.index,
                duration: parseInt(local.currentVideo.duration),
            },function(data){
                thisElement.classList.add('fa-play-circle-o');
                thisElement.classList.remove('fa-arrow-circle-left');
                thisElement.innerText = '本机播放';
                document.getElementById('circleProgress').style.display = '';
                document.getElementById('videoPlayer').style.display = 'none';
                updateButton(false);
                mui.later(function(){
                    mask.close();
                }, 100);
            });
        } else if (hasClass(this, 'fa-play-circle-o')) {
            mask.show();
            global.chimee = createChimee();
            local.currentPlaylist.name = global.currentPlaylist.name;
            local.currentPlaylist.index = global.currentPlaylist.index;
            local.currentVideo.path = global.currentVideo.path;
            local.currentVideo.name = global.currentVideo.name;
            local.currentVideo.position = global.currentVideo.position;
            local.currentVideo.duration = global.currentVideo.duration;
            showVideoPlayer(global.chimee, global.currentVideo.position, global.currentPlaylist.index, false);
            pauseVideo(function(data) {
                global.chimee.load(global.apiUrl
                                + '?index=' + global.currentPlaylist.index
                                + '&command=playAtApp&r=' + new Date().getTime());
                thisElement.classList.remove('fa-play-circle-o');
                thisElement.classList.add('fa-arrow-circle-left');
                thisElement.innerText = '返回投屏';
                updateButton(true);
                mui.later(function(){
					mask.close();
				}, 100);
			});
        }
    });

    function showVideoPlayer(chimee, currentVideoPosition, currentVideoIndex, autoFullScreen) {
        document.getElementById('circleProgress').style.display = 'none';
        document.getElementById('videoPlayer').style.display = '';
        global.isLocal = true;
        let flag = -1;
        let end = false;
        global.chimee.on('timeupdate', function() {
            if (end || isNaN(chimee.duration) || chimee.duration == 0)
                return;
            if (flag == -1 && chimee.currentTime > 0.3) {
                flag = 1;
                /*
                if (autoFullScreen) {
                    chimee.requestFullscreen('container');
                }*/
                let offset = global.currentPlaylist.skipHead;
                if (currentVideoPosition > global.currentPlaylist.skipHead)
                    offset = currentVideoPosition - 3
                chimee.currentTime = offset
            }
            if (global.currentPlaylist.length == currentVideoIndex - 1)
                return
            let leftTime = chimee.duration - (chimee.currentTime + global.currentPlaylist.skipTail);
            if (leftTime <= 1 ) {
                end = true;
                chimee.exitFullscreen();
                let nextVideoIndex = currentVideoIndex + 1;
                if (nextVideoIndex > global.currentPlaylist.videoList.length - 1) {
                    chimee.pause()
                }
                let nextVideoName = global.currentPlaylist.videoList[nextVideoIndex];
                destroyChimee();
                global.chimee = createChimee();
                showVideoPlayer(global.chimee, 0, nextVideoIndex, true);
                global.chimee.load(global.apiUrl
                                + '?index=' + nextVideoIndex
                                + '&command=playAtApp&r=' + new Date().getTime());

                updateLocalData({
                    currentPlaylist: {
                        index: nextVideoIndex,
                    },
                    currentVideo: {
                        name: nextVideoName,
                    }
                });
            }
            updateLocalData({
                currentVideo: {
                    position: Math.round(chimee.currentTime),
                    duration: Math.round(chimee.duration),
                }
            });

        });

    }

    function playVideoLocal(index) {
        global.chimee.exitFullscreen();
        if (index > global.currentPlaylist.videoList.length - 1) {
            chimee.pause()
        }
        let videoName = global.currentPlaylist.videoList[index];
        destroyChimee();
        global.chimee = createChimee();
        showVideoPlayer(global.chimee, 0, index, true);
        global.chimee.load(global.apiUrl
            + '?index=' + index
            + '&command=playAtApp&r=' + new Date().getTime());
        updateLocalData({
            currentPlaylist: { index: index, },
            currentVideo: { name: videoName, }
        });

    }

    function destroyChimee() {
        global.chimee.destroy();
        global.chimee = undefined;
    }

    function createChimee() {
        return new ChimeeMobilePlayer({
                wrapper: '#videoPlayer',
                controls: true,
                autoplay: true,
                x5VideoPlayerFullscreen: true,
                x5VideoOrientation: 'portrait',
                xWebkitAirplay: true,
                width:'100%',
                height:'100%',
            });
    }

    document.getElementById('buttonPlaylistMenu').addEventListener('tap', function() {
        setTimeout(function(){
            var targetEle = document.querySelector('ul#video-file-list li button.mui-btn.fa.mui-btn-danger');
            zenscroll.center(targetEle, 0)
        }, 1);
    });

    function createPlaylistVideos(file_name_list, index) {
        videoFileList = document.getElementById('video-file-list');
		videoFileList.innerHTML = '';
        for (let i = 0; i < file_name_list.length; i++) {
            let li = document.createElement('li');
            li.className = 'mui-table-view-cell';
            let spanName = document.createElement('span');
            spanName.className = 'playlist-video-item-name';
            spanName.innerHTML = file_name_list[i];
            let btn = document.createElement('button');
            btn.setAttribute('videoName', file_name_list[i])
            btn.className = 'mui-btn fa';
            btn.setAttribute('videoIndex', "" + i)
            let playlistProgressText = document.createElement('span');
            playlistProgressText.className = 'playlist-progress-text';

            let playlistProgress = document.createElement('div');
            playlistProgress.className = 'playlist-progress';
            playlistProgress.style.width = '0%'

            li.appendChild(spanName);
            li.appendChild(playlistProgressText);
            li.appendChild(btn);
            li.appendChild(playlistProgress);
            btn.addEventListener('tap', function() {
                currentIndex = -1;
                if (hasClass(this, 'fa-play')) {
                    currentIndex = parseInt(this.getAttribute('videoIndex'));
                }
                if (global.isLocal) {
                    playVideoLocal(currentIndex);
                } else {
                    playVideo(currentIndex, this.getAttribute('videoName'), global.viewPlaylist.name);
                }

            });
            videoFileList.appendChild(li);
        }
        updatePlaylistVideoStatus({}, global);
    }

    function updatePlaylistVideoStatus(data, context) {
        isLocalData = (context == local);
        if (!isLocalData) {
            if (data.viewPlaylist && data.viewPlaylist.index)
                global.viewPlaylist.index = data.viewPlaylist.index;
            if (data.dlnaPlayer && data.dlnaPlayer.status)
                global.dlnaPlayer.status = data.dlnaPlayer.status;
        }
        let rows = document.querySelectorAll('#video-file-list li');
        let currentIndex = -1;
        if (isLocalData) {
            currentIndex = local.currentPlaylist.index;
        } else {
            currentIndex = global.viewPlaylist.index
        }
        for (let j = 0 ; j < rows.length ; j++ ) {
            let btn = rows[j].querySelector('button');
            let playlistProgress = rows[j].querySelector('.playlist-progress');
            let playlistProgressText = rows[j].querySelector('.playlist-progress-text');
            if ( j != currentIndex ) {
                rows[j].classList.remove('playing');
                rows[j].querySelector('.playlist-progress-text').innerHTML = '';
                rows[j].querySelector('.playlist-progress').style.width = 0;
                btn.classList.remove('fa-stop');
                btn.classList.add('fa-play');
                btn.classList.remove('mui-btn-danger');
                btn.classList.add('mui-btn-primary');
            } else {
                rows[j].classList.add('playing')
                if(!isLocalData && (global.currentPlaylist.name != global.viewPlaylist.name)) {
                    btn.classList.remove('fa-stop');
                    btn.classList.add('fa-play');
                } else if (!isLocalData && (global.dlnaPlayer.status == 'Stop' || btn.getAttribute('videoName') != global.currentVideo.name)) {
                    btn.classList.remove('fa-stop');
                    btn.classList.add('fa-play');
                } else {
                    btn.classList.remove('fa-play');
                    btn.classList.add('fa-stop');
                }
                btn.classList.remove('mui-btn-primary');
                btn.classList.add('mui-btn-danger');
            }

        }

        updatePlaylistProgress();
    }

    function updatePlaylistProgress() {
        let playingRow = document.querySelector('#video-file-list > li.mui-table-view-cell.playing');
        let playingVideoProgressText = playingRow.querySelector('.playlist-progress-text')
        let playlistProgress = playingRow.querySelector('.playlist-progress');
        percent = -1;
        if (global.currentPlaylist.name == global.viewPlaylist.name) {
            if (global.currentVideo.duration > 0) {
                percent = global.currentVideo.position / global.currentVideo.duration * 100
            }
        } else if (global.viewPlaylist.duration > 0) {
            percent = global.viewPlaylist.position / global.viewPlaylist.duration * 100
        }
        if (percent > -1) {
            playlistProgress.style.width = (percent > 1 ? percent.toFixed(0) : 1) + '%';
            playingVideoProgressText.innerText = '(已播放:' + percent.toFixed(2) + '%)'
        }

    }


    updateData();
    getAllPlaylist();
    setInterval(updateData, 500)

    function playVideo(index, fileName, playlistName) {
        mui.getJSON(
                global.apiUrl,
                {
                    command:'index',
                    index: index,
                    name: fileName,
                    playlistName: playlistName,
                    r: '' + new Date().getTime(),
                },
                function(data){
                    updatePlaylistVideoStatus(data, global);
                }
         );
    }

    function pauseVideo(callback) {
        mui.getJSON(global.apiUrl,{command:'pause', r: '' +new Date().getTime()}, callback);
    }

    function resumeVideo(callback) {
        mui.getJSON(global.apiUrl,{command:'play', r: '' +new Date().getTime()}, callback);
    }

    function stopVideo(callback) {
        mui.getJSON(global.apiUrl,{command:'stop', r: '' +new Date().getTime()}, callback);
    }

    function seek(offset, callback) {
        mui.getJSON(global.apiUrl,{command:'seek', pos:offset, r: '' +new Date().getTime()}, callback);
    }
});