from logging import getLogger, StreamHandler, FileHandler, Formatter, INFO, ERROR


def init_logger():
    logger = getLogger("th_ura_summary")

    # StreamHandlerの設定
    ch = StreamHandler()
    ch.setLevel("INFO")  # ハンドラーにもそれぞれログレベル、フォーマットの設定が可能
    ch_formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.addHandler(ch)  # StreamHandlerの追加
