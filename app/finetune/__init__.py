"""Supervised fine-tuning (SFT) dataset assembly for LoRA training (Week 4).

Turns the project's labeled QA sets into instruction/response pairs, formats
them to a chat template, and splits train/val. Training itself runs on a free
Colab/Kaggle GPU; this package produces the data and the format.
"""
