import pickle
import tempfile

from django.core.files.base import File
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.conf import settings

from ratings.models import Rating
from playlists.models import MovieProxy
from surprise import accuracy, Reader, Dataset, SVD
from surprise.model_selection import cross_validate

from exports import storages as exports_storages



def export_ratings_dataset():
    ctype = ContentType.objects.get_for_model(MovieProxy, for_concrete_model=False)
    qs = Rating.objects.filter(active=True, content_type=ctype)
    qs = qs.annotate(userId=F('user_id'),movieId=F('object_id'),rating=F('value'))
    return qs.values('userId', 'movieId', 'rating') # -> [{}]


def get_data_loader(dataset, columns=['userId', 'movieId', 'rating']):
    # having the import inside the function can help in case of errors
    import pandas as pd
    # DataFrame: A two-dimensional labeled data structure with columns that can hold different types of data
    # dropna() removes rows containing NaN
    # inplace=True modifies the DataFrame directly, rather than returning a copy with the changes
    df = pd.DataFrame(dataset)
    df['rating'].dropna(inplace=True)
    max_rating, min_rating = df.rating.max(), df.rating.min()
    # Adding rating scale
    reader = Reader(rating_scale=(min_rating, max_rating))
    # Return the dataframe whit 'userId', 'movieId', 'rating' colums
    return Dataset.load_from_df(df[columns], reader)


def get_model_acc(trainset, model, use_rmse=True):
    testset = trainset.build_testset()
    predictions = model.test(testset)
    # RMSE should be low as we are biased
    if not use_rmse:
        return accuracy.mae(predictions, verbose=True)
    acc = accuracy.rmse(predictions, verbose=True)
    return acc 

def train_surprise_model(n_epochs=20, verbose=True):
    ''' Setting surprise'''
    dataset = export_ratings_dataset()
    loaded_data = get_data_loader(dataset)
    # Declaring the algoritm
    model = SVD(n_epochs=n_epochs, verbose=verbose) 
    # n_epochs: This parameter controls how many times the algorithm should go over 
    # the entire dataset to update the latent factors.
    
    # Cross validate will compare the algoritm whit the data across RMSE function and MAE function
    # Use to improve the training process
    cv_results = cross_validate(model, loaded_data, measures=['RMSE', "MAE"], cv=4, verbose=True)
    
    # Training
    # It converts the entire dataset (both training and testing portions) into a Trainset object, 
    # which is a format that Surprise's algorithms can work with. This allows you to train a 
    # recommendation algorithm on all available data.
    trainset = loaded_data.build_full_trainset()
    model.fit(trainset)
    
    # Grab the testset and some prediction from that testset
    acc = get_model_acc(trainset, model, use_rmse=True)
    
    acc_label = int(100* acc)
    model_name = f"model-{acc_label}" # model-0.63
    export_model(model, model_name, model_type='surprise', model_ext='pkl', verbose=True)
    
    
def export_model(model, model_name='model', model_type='surprise', model_ext='pkl', verbose=True):
    with tempfile.NamedTemporaryFile(mode='rb+') as temp_f:
        pickle.dump({"model": model}, temp_f)
        path = f"ml/models/{model_type}/{model_name}.{model_ext}"
        path_latest = f"ml/models/{model_type}/latest.{model_ext}"
        if verbose:
            print(f"Exporting to {path} and {path_latest}")
        exports_storages.save(path, File(temp_f))
        exports_storages.save(path_latest, File(temp_f), overwrite=True)


def load_model(model_type='surprise', model_ext='pkl'):
    path_latest = settings.MEDIA_ROOT / f"ml/models/{model_type}/latest.{model_ext}"
    model = None
    if path_latest.exists():
        with open(path_latest, 'rb') as f:
            model_data = pickle.load(f)
            model = model_data.get('model')
    else:
        raise ValueError("No model found.")
    return model
    