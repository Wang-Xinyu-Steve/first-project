class AudioParserBase:
    def get_audio_info(self, url):
        """
        输入音频页面链接，返回包含音频直链和元信息的字典。
        必须由子类实现。
        """
        raise NotImplementedError("子类必须实现 get_audio_info 方法") 