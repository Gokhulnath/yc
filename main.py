from helper.company_list import *
from helper.dowload_all_company_html import get_all_companies_html
from helper.insert_company_list import *

def get_all_batch_based_companies():
    batches = ["X25", "W25", "F24", "S24", "W24", "S23", "W23", "S22", "W22", "S21", "W21", "S20", "W20", "S19", "W19",
               "S18", "W18", "S17", "W17", "IK12", "S16", "W16", "S15", "W15", "S14", "W14", "S13", "W13", "S12", "W12",
               "S11", "W11", "S10", "W10", "S09", "W09", "S08", "W08", "S07", "W07", "S06", "W06", "S05"]
    for batch in batches:
        url = f'https://www.ycombinator.com/companies?batch={batch}'  # Replace with your URL
        companies = initiate_extraction(url)
        batch_data = {
            "batch": batch,
            "batch_link": url,
            "companies": companies
        }
        insert_data(batch_data)


def main():
    try:
        # get_all_batch_based_companies()
        get_all_companies_html()
        print("If you see this message, the application is fucking working fine")
    except Exception as e:
        print(e)
        print("If you see this message, congrats the application is fucked up asshole!")

if __name__ == "__main__":
    main()
