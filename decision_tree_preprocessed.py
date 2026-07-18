import os
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score
from data_preprocessing import preprocess_from_double_extension_excel


def load_preprocessed_data(train_path='preprocessed_train.csv', test_path='preprocessed_test.csv', use_reduced_features=False):
    if not os.path.exists(train_path) or not os.path.exists(test_path):
        print('[Preprocess] Missing preprocessed files. Generating now...')
        preprocess_from_double_extension_excel()

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    if 'Decision' not in train_df.columns or 'Decision' not in test_df.columns:
        raise ValueError("Expected 'Decision' column in preprocessed data.")

    if use_reduced_features:
        excluded = {'Decision', 'Channel_Utilization'}
        feature_columns = [col for col in train_df.columns if col not in excluded]
    else:
        feature_columns = [col for col in train_df.columns if col != 'Decision']

    X_train = train_df[feature_columns]
    y_train = train_df['Decision']
    X_test = test_df[feature_columns]
    y_test = test_df['Decision']

    return X_train, X_test, y_train, y_test, feature_columns


def train_decision_tree(X_train, y_train, max_depth=4, min_samples_leaf=20, max_features='sqrt', random_state=42):
    model = DecisionTreeClassifier(
        criterion='entropy',
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        random_state=random_state,
    )
    model.fit(X_train, y_train)
    return model


def evaluate_cross_validation(X, y, cv=5, random_state=42):
    cv_split = StratifiedKFold(n_splits=cv, shuffle=True, random_state=random_state)
    model = DecisionTreeClassifier(
        criterion='entropy',
        max_depth=4,
        min_samples_leaf=20,
        max_features='sqrt',
        random_state=random_state,
    )
    scores = cross_val_score(model, X, y, cv=cv_split, scoring='accuracy')

    print('=== Cross-Validation ===')
    print(f'Fold accuracies: {scores}')
    print(f'Mean accuracy: {scores.mean():.4f}, Std: {scores.std():.4f}')
    return scores


def evaluate_model(model, X_test, y_test):
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(y_test, predictions)
    matrix = confusion_matrix(y_test, predictions)

    print('=== Decision Tree Evaluation ===')
    print(f'Test samples: {X_test.shape[0]}')
    print(f'Features used: {len(X_test.columns)}')
    print(f'Accuracy: {accuracy:.4f}')
    print('\nClassification Report:')
    print(report)
    print('Confusion Matrix:')
    print(matrix)

    return accuracy, report, matrix


if __name__ == '__main__':
    X_train, X_test, y_train, y_test, feature_columns = load_preprocessed_data(use_reduced_features=True)
    X_all = pd.concat([X_train, X_test], ignore_index=True)
    y_all = pd.concat([y_train, y_test], ignore_index=True)

    print('Loaded preprocessed training and test data:')
    print(f'  Train shape: {X_train.shape}')
    print(f'  Test shape: {X_test.shape}')
    print(f'  Feature columns: {feature_columns}')
    print('  Note: Channel_Utilization is excluded from features to avoid trivial label leakage.')

    print('\nPerforming cross-validation on the full dataset...')
    evaluate_cross_validation(X_all, y_all)

    model = train_decision_tree(X_train, y_train)
    evaluate_model(model, X_test, y_test)
