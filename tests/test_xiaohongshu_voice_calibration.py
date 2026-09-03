from __future__ import annotations

from decision_kernel.xiaohongshu_harness import load_style_sample_bank


def test_positive_sample_bank_keeps_sentence_level_voice_anchors() -> None:
    bank = load_style_sample_bank()
    samples = {sample.sample_id: sample for sample in bank.samples}

    yunnan = samples["yunnan-germanium-industry-odds"]
    hengtong = samples["hengtong-expectation-repricing"]
    gigadevice = samples["gigadevice-normalized-earnings"]
    dongshan = samples["dongshan-earnings-path-reunderwrite"]
    shengyi = samples["shengyi-sotp-implied-earnings"]

    assert all(
        sample.performance_label == "HIGH_READ"
        for sample in (yunnan, hengtong, gigadevice, dongshan, shengyi)
    )
    assert any("真正的问题，不是能不能暴利。而是能暴利多久" in item for item in yunnan.reusable_lessons)
    assert any("产品目录只能证明" in item for item in hengtong.reusable_lessons)
    assert any("150亿元利润和30倍PE可以同时成立" in item for item in gigadevice.reusable_lessons)
    assert any("不是价格变了，而是更高盈利路径的可信度提高了" in item for item in dongshan.reusable_lessons)
    assert any("当前价格还 price in 了多少预期" in item for item in shengyi.reusable_lessons)


def test_negative_calibration_remains_separate() -> None:
    bank = load_style_sample_bank()
    samples = {sample.sample_id: sample for sample in bank.samples}

    assert samples["demingli-overloaded-negative"].performance_label == "LOW_READ"
