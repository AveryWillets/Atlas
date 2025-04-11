# Importing necessary libraries
from PyQt5.QtWidgets import QApplication, QWidget, QTableView, QVBoxLayout, QPushButton, QFileDialog, QHBoxLayout, QLabel, QTextEdit
from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QColor
import pandas as pd
import numpy as np
import sys
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Class for data
class AtlasApp(QWidget):
    def __init__(self):
        super().__init__()

        # Function for user to upload file
        self.df = pd.DataFrame()     

        # Reading data (hardcoded path for debugging)
        #self.df = pd.read_csv(r"C:\Users\avery\vs_python\Atlas\dummy_dataset.csv")

        # Caches for errors
        self.cell_errors = {}
        self.column_errors = {}

        #self.calculate_errors()

        self.init_ui()
        self.load_file()


    def init_ui(self):
        # Setting window name and size
        self.setWindowTitle("Atlas")
        self.resize(1200, 800)

        # Create the new horizontal layout that splits left and right
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # --- Left side: table + buttons ---
        self.table = QTableView()
        left_layout.addWidget(self.table)

        # Load and Save buttons
        load_button = QPushButton("Load CSV/TSV", self)
        load_button.clicked.connect(self.load_file)
        left_layout.addWidget(load_button)

        save_button = QPushButton("Save Data", self)
        save_button.clicked.connect(self.save_data)
        left_layout.addWidget(save_button)

        # --- Right side: error summary panel ---
        self.summary_box = QTextEdit()
        self.summary_box.setReadOnly(True)

        right_layout.addWidget(QLabel("📊 Error Summary"))
        right_layout.addWidget(self.summary_box)

        # Creating matplotlib figure for summary stats
        self.figure = Figure(figsize=(4, 3))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)

        # Combine into main layout
        main_layout.addLayout(left_layout, stretch=3)
        main_layout.addLayout(right_layout, stretch=1)

        # Set final layout
        self.setLayout(main_layout)


    # Finding errors in data
    def calculate_errors(self):
        for col_idx, column in enumerate(self.df.columns):
            dtype = self.df[column].dtype
            col_has_error = set()

            for row_idx, value in self.df[column].items():
                errors = []

                # Check null
                if pd.isna(value):
                    errors.append("null")
                    col_has_error.add("null")

                # Check type mismatch
                if not self.is_valid_datatype(value, dtype):
                    errors.append("type")
                    col_has_error.add("type")

                # Check outliers
                if self.is_outlier(column, value):
                    errors.append("outlier")
                    col_has_error.add("outlier")

                if errors:
                    self.cell_errors[(row_idx, col_idx)] = errors

            if col_has_error:
                self.column_errors[col_idx] = col_has_error

        # Printing error cells (for debugging purposes)
        print(f"cell_errors: {self.cell_errors}")
        print(f"column_errors: {self.column_errors}")

    # Filter function: datatype
    def is_valid_datatype(self, value, expected_dtype):
        if pd.isna(value):  # skip NaNs for type checking
            return True
        if np.issubdtype(expected_dtype, np.integer):
            return isinstance(value, int) or str(value).isdigit()
        elif np.issubdtype(expected_dtype, np.floating):
            try:
                float(value)
                return True
            except ValueError:
                return False
        elif expected_dtype == object:
            return isinstance(value, str)
        return True

    # Filter function: outlier
    def is_outlier(self, column, value):
        if not np.issubdtype(self.df[column].dtype, np.number):
            return False
        if pd.isna(value):
            return False

        try:
            val = float(value)
            mean = self.df[column].mean()
            std = self.df[column].std()
            return abs(val - mean) > 3 * std
        except:
            return False

    # Saving data
    def save_data(self):
        updated_df = self.df.copy()
        updated_df.to_csv("updated_data.csv", index=False)
        print("Data saved to updated_data.csv")

    from PyQt5.QtWidgets import QFileDialog

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Data Files (*.csv *.tsv);;All Files (*)"
        )

        if file_path:
            try:
                if file_path.endswith(".tsv"):
                    df = pd.read_csv(file_path, sep="\t")
                else:
                    df = pd.read_csv(file_path)

                # Validation checking
                if df.empty:
                    raise ValueError("File contains no data.")

                if df.columns.isnull().any():
                    raise ValueError("File is missing headers.")

                self.df = df
                self.cell_errors = {}
                self.column_errors = {}

                self.calculate_errors()

                # Update model and table
                self.model = PandasModel(self.df, self.cell_errors, self.column_errors)
                # Connect model's dataChanged signal to refresh summary
                self.model.dataChanged.connect(self.handle_data_changed)
                self.table.setModel(self.model)

                # Update error summary panel
                self.update_error_summary()

            except Exception as e:
                print(f"Failed to load file: {e}")

    def update_error_summary(self):
        total_cells = self.df.shape[0] * self.df.shape[1]
        error_counts = {
            "null": 0,
            "type": 0,
            "outlier": 0
        }

        for errors in self.cell_errors.values():
            for error in errors:
                error_counts[error] += 1

        summary_lines = []
        for error_type, count in error_counts.items():
            percent = (count / total_cells) * 100
            summary_lines.append(f"{error_type.capitalize()} Errors: {count} ({percent:.2f}%)")

        total_errors = sum(error_counts.values())
        summary_lines.append(f"\nTotal Errors: {total_errors}")
        summary_lines.append(f"Total Cells: {total_cells}")

        self.summary_box.setText("\n".join(summary_lines))

        self.draw_error_chart()


    def handle_data_changed(self, topLeft, bottomRight, roles):
        # Recalculate errors and update the model
        self.calculate_errors()
        self.model.update_errors(self.cell_errors, self.column_errors)

        # Update summary view
        self.update_error_summary()

    def draw_error_chart(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        error_types = ['null', 'type', 'outlier']
        counts = [0, 0, 0]
        for errors in self.cell_errors.values():
            for err in errors:
                if err in error_types:
                    counts[error_types.index(err)] += 1

        ax.bar(error_types, counts, color=['red', 'orange', 'blue'])
        ax.set_ylabel("Count")
        ax.set_title("Error Distribution")

        self.canvas.draw()



# Class for GUI model
class PandasModel(QAbstractTableModel):
    def __init__(self, df, cell_errors, column_errors):
        super().__init__()
        self.df = df
        self.cell_errors = cell_errors
        self.column_errors = column_errors

    def rowCount(self, parent=None):
        return self.df.shape[0]

    def columnCount(self, parent=None):
        return self.df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        col = index.column()

        if role == Qt.DisplayRole:
            return str(self.df.iloc[row, col])

        elif role == Qt.BackgroundRole:
            # Deep color for cell errors
            if (row, col) in self.cell_errors:
                return self.get_error_color(self.cell_errors[(row, col)], dark=True)

            # Light color if column has error
            elif col in self.column_errors:
                return self.get_error_color(self.column_errors[col], dark=False)

        elif role == Qt.ForegroundRole:
            if (row, col) in self.cell_errors:
                return QColor("white")
            return QColor("black")

        return None


    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.df.columns[section]
            else:
                return section
        return None

    # Determining error filter colors
    def get_error_color(self, error_types, dark=False):
        color_map = {
            "null": QColor(255, 0, 0),
            "type": QColor(255, 255, 0),
            "outlier": QColor(51, 153, 255),
        }

        # Blend error colors in same column together
        base = np.array([0, 0, 0], dtype=float)
        for etype in error_types:
            rgb = np.array(color_map[etype].getRgb()[:3])
            base += rgb
        base /= len(error_types)

        if not dark:
            # Lighten the color
            base = base + (255 - base) * 0.7

        return QColor(int(base[0]), int(base[1]), int(base[2]))
    
    def update_errors(self, cell_errors, column_errors):
        self.cell_errors = cell_errors
        self.column_errors = column_errors
        self.layoutChanged.emit()  # Refresh the view

# Run app
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AtlasApp()
    window.show()
    sys.exit(app.exec_())