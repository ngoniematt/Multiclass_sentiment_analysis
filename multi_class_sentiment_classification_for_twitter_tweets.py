# -*- coding: utf-8 -*-
"""Multi-Class Sentiment Classification for twitter tweets.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1gXYnL-KeeYieMcGosqFRnP_JmjoZ9rit
"""

!pip install transformers
!pip install accelerate
!pip install datasets
!pip install bertviz #Bert visualisation
!pip intsall umap-learn
!pip install seaborn --upgrade

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv("https://raw.githubusercontent.com/ngoniematt/Multiclass_sentiment_analysis/refs/heads/main/twitter_multi_class_sentiment.csv")

df

df.info()

df.isnull().sum()

df.describe()

df['label'].value_counts()



"""**DATASET ANALYSIS**

"""

import matplotlib.pyplot as plt

lable_count = df['label_name'].value_counts(ascending = True)
lable_count

lable_count.plot(kind = 'barh')
plt.title('Frequency of Classes')
plt.show()

df["words per tweet"] = df['text'].str.split().apply(len)
df

df.boxplot('words per tweet', by = 'label_name', figsize = (12,6))

"""**HOW TOKENIZATION IS DONE**"""

from transformers import AutoTokenizer
model_ckpt = "bert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_ckpt)

text = "My name is Mathew and i love NLP"
encoded_text = tokenizer(text)
print(encoded_text)

len(tokenizer.vocab)

len(tokenizer.vocab), tokenizer.vocab_size, tokenizer.model_max_length



"""**DATA LOADER AND TRAIN TEST SPLIT**"""

from sklearn.model_selection import train_test_split

train, test = train_test_split(df, test_size = 0.3,stratify = df['label_name']) #Getting the train set which will be 70%
test, validation = train_test_split(test, test_size = 1/3,stratify = test['label_name']) #Getting the validationset from the test set
train.shape, test.shape, validation.shape

from datasets import Dataset,DatasetDict

dataset = DatasetDict({
    'train': Dataset.from_pandas(train, preserve_index= False),
    'test': Dataset.from_pandas(test, preserve_index= False),
    'validation': Dataset.from_pandas(validation, preserve_index= False)
})

dataset

"""**TOKENIZATION OF THE EMOTION/SENTIMENT DATA**"""

dataset [ 'train' ][ 0], dataset [ 'train' ][ 1]

def tokenize(batch):
  return tokenizer(batch['text'], padding = True, truncation = True)


print(tokenize(dataset['train'][:2]))

emotion_encoded= dataset.map(tokenize, batched = True, batch_size = None)

emotion_encoded

#Label2id, id2Lable

label2id = {x['label_name']:x['label'] for x in dataset['train']}
id2label = {v:k for k,v in label2id.items()}

label2id, id2label

"""**MODEL BUILDING**"""

from transformers import AutoModel
import torch

model = AutoModel.from_pretrained(model_ckpt)

model

model.config.architectures

"""**LOADING MODEL FOR CLASSIFICATION WITH CLASSIFICATION HEAD**"""

from transformers import AutoModelForSequenceClassification, AutoConfig

num_lables = len(label2id)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
config = AutoConfig.from_pretrained(model_ckpt,label2id = label2id, id2label = id2label)
model = AutoModelForSequenceClassification.from_pretrained(model_ckpt, config = config).to(device)

device

#check the model and compare with the previous
model

model.config

"""**BUILDING TRAINING ARGUMENTS**"""

from transformers import TrainingArguments

batch_size = 64
training_dr = "bert-base-uncased-train_dr"

training_args = TrainingArguments( output_dir= training_dr,
                                  overwrite_output_dir= True,
                                  eval_strategy= 'epoch',
                                   num_train_epochs = 2,
                                   learning_rate = 2e-5,
                                   per_device_train_batch_size = batch_size,
                                   per_device_eval_batch_size = batch_size,
                                   weight_decay=0.01,
                                   disable_tqdm= False,
                                   report_to="none"  # This disables WandB and other integrations

)

"""**BUILDING COMPUTE METRICS**"""

#Build compute metrics function
!pip install evaluate
import evaluate
import numpy as np
metric = evaluate.load('accuracy')
def compute_metrics_evaluate(eval_pred):
  predictions, labels = eval_pred
  predictions = np.argmax(predictions, axis = -1)
  return accuracy.compute(predictions = predictions, references = labels)

#use default sklearn to build compute metrics
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

def compute_metrics_sklearn(pred):
  labels = pred.label_ids
  preds = pred.predictions.argmax(-1)

  f1 = f1_score(labels, preds, average = 'weighted')
  precision = precision_score(labels, preds, average = 'weighted')
  recall = recall_score(labels, preds, average = 'weighted')
  accuracy = accuracy_score(labels, preds)

  return {'f1': f1, 'precision': precision, 'recall': recall, 'accuracy': accuracy}

"""**BUILD TRAINER AND DO TRAINING**"""

from transformers import Trainer
trainer = Trainer(
    model = model,
    args = training_args,
    train_dataset = emotion_encoded['train'],
    eval_dataset = emotion_encoded['validation'],
    tokenizer = tokenizer,
    compute_metrics = compute_metrics_sklearn
)

trainer.train()

"""**MODEL EVALUATION**"""

preds_output = trainer.predict(emotion_encoded['test'])
preds_output.metrics

y_pred = np.argmax(preds_output.predictions, axis = -1)
y_true = emotion_encoded['test']['label']

from sklearn.metrics import classification_report
print(classification_report(y_true, y_pred, ))

"""**PLOT CONFUSION MATRIX**"""

import seaborn as sns
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt

cm = confusion_matrix(y_true, y_pred)
cm

plt.figure(figsize = (5,5))
sns.heatmap(cm, annot = True, cmap = 'Blues', xticklabels = label2id.keys(), yticklabels = label2id.keys(), fmt = 'd', cbar = False)
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.show()

"""**SAVE MODEL AND DO PREDICTION ON CUSTOM DATA**"""

text = "I am super happy today. I got it done. Finally!!"

input_encoded = tokenizer(text, return_tensors = 'pt').to(device)
input_encoded

with torch.no_grad():
  output = model(**input_encoded)
output

logits = output.logits
logits

pred = torch.argmax(logits, dim = -1).item()
pred, id2label[pred]

#Lets put everything in a function
def get_predict(text):
  input_encoded = tokenizer(text, return_tensors = 'pt').to(device)
  with torch.no_grad():
    output = model(**input_encoded)
  logits = output.logits
  pred = torch.argmax(logits, dim = -1).item()
  return id2label[pred]

get_predict(text)

trainer.save_model("bert-base-uncased-matt")

#use pipeline for prediction

from transformers import pipeline
classifier = pipeline('text-classification', model = 'bert-base-uncased-matt', tokenizer = model_ckpt)

classifier([text,'hello how are you?','i feel low today'])

from google.colab import files
files.download('/content/bert-base-uncased-matt')

import streamlit as st